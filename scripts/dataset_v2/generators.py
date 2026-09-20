"""Image generation operations for Dataset V2 variants."""

import random
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple, List
from PIL import Image, ImageEnhance, ImageFilter
import cv2


class NaturalProcessingGenerator:
    """Generates natural-processing variants."""

    @staticmethod
    def jpeg_recompress(image: Image.Image, quality: int) -> Image.Image:
        """Apply JPEG recompression."""
        import io
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)
        return Image.open(buffer)

    @staticmethod
    def resize(image: Image.Image, scale: float) -> Image.Image:
        """Resize image by scale factor."""
        new_width = int(image.width * scale)
        new_height = int(image.height * scale)
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    @staticmethod
    def sharpen(image: Image.Image, strength: float) -> Image.Image:
        """Apply sharpening."""
        enhancer = ImageEnhance.Sharpness(image)
        return enhancer.enhance(strength)

    @staticmethod
    def adjust_brightness(image: Image.Image, factor: float) -> Image.Image:
        """Adjust brightness (factor: 0.5=darker, 1.0=original, 1.5=brighter)."""
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(factor)

    @staticmethod
    def adjust_contrast(image: Image.Image, factor: float) -> Image.Image:
        """Adjust contrast (factor: 0.5=lower, 1.0=original, 1.5=higher)."""
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)

    @staticmethod
    def adjust_color(image: Image.Image, factor: float) -> Image.Image:
        """Adjust color saturation (factor: 0.5=desaturated, 1.0=original, 1.5=saturated)."""
        enhancer = ImageEnhance.Color(image)
        return enhancer.enhance(factor)


class ManipulationGenerator:
    """Generates manipulated variants."""

    @staticmethod
    def copy_move(
        image: Image.Image,
        source_region: Tuple[int, int, int, int],
        dest_region: Tuple[int, int, int, int],
        rotation: int = 0,
        scale: float = 1.0,
        blend: float = 0.0
    ) -> Tuple[Image.Image, np.ndarray]:
        """
        Perform copy-move manipulation with controlled diversity.

        Args:
            image: Source image
            source_region: (x, y, width, height) of source region
            dest_region: (x, y, width, height) of destination region
            rotation: Rotation angle in degrees (0, 90, 180, 270)
            scale: Scale factor (0.8-1.2 typical range)
            blend: Blending strength (0-1, 0 = no blending)

        Returns:
            Tuple of (manipulated image, mask)
        """
        img_array = np.array(image)
        mask = np.zeros((image.height, image.width), dtype=np.uint8)

        # Extract source region
        sx, sy, sw, sh = source_region
        source_patch = img_array[sy:sy+sh, sx:sx+sw].copy()

        # Apply transformations
        if rotation != 0:
            # Full rotation support
            M = cv2.getRotationMatrix2D((sw//2, sh//2), rotation, 1.0)
            source_patch = cv2.warpAffine(source_patch, M, (sw, sh))

        if scale != 1.0:
            new_w = int(sw * scale)
            new_h = int(sh * scale)
            source_patch = cv2.resize(source_patch, (new_w, new_h))

        # Paste at destination with optional blending
        dx, dy, dw, dh = dest_region
        patch_h, patch_w = source_patch.shape[:2]
        
        # Ensure patch fits in destination - adjust destination if needed
        actual_dw = max(patch_w, dw)
        actual_dh = max(patch_h, dh)
        
        # Ensure destination is within image bounds
        if dx + actual_dw > image.width:
            actual_dw = image.width - dx
        if dy + actual_dh > image.height:
            actual_dh = image.height - dy
        
        # Resize patch to fit if needed
        if patch_w > actual_dw or patch_h > actual_dh:
            source_patch = cv2.resize(source_patch, (actual_dw, actual_dh))
            patch_h, patch_w = source_patch.shape[:2]
        
        # Paste with optional blending
        if patch_h > 0 and patch_w > 0:
            if blend > 0:
                # Simple alpha blending at edges
                blended_patch = source_patch.copy()
                edge_width = max(1, int(min(patch_w, patch_h) * 0.1))
                
                # Create edge fade
                if edge_width < patch_h:
                    blended_patch[:edge_width, :] = (
                        blended_patch[:edge_width, :] * (1 - blend) + 
                        img_array[dy:dy+edge_width, dx:dx+patch_w] * blend
                    ).astype(np.uint8)
                    blended_patch[-edge_width:, :] = (
                        blended_patch[-edge_width:, :] * (1 - blend) + 
                        img_array[dy+patch_h-edge_width:dy+patch_h, dx:dx+patch_w] * blend
                    ).astype(np.uint8)
                if edge_width < patch_w:
                    blended_patch[:, :edge_width] = (
                        blended_patch[:, :edge_width] * (1 - blend) + 
                        img_array[dy:dy+patch_h, dx:dx+edge_width] * blend
                    ).astype(np.uint8)
                    blended_patch[:, -edge_width:] = (
                        blended_patch[:, -edge_width:] * (1 - blend) + 
                        img_array[dy:dy+patch_h, dx+patch_w-edge_width:dx+patch_w] * blend
                    ).astype(np.uint8)
                
                img_array[dy:dy+patch_h, dx:dx+patch_w] = blended_patch
            else:
                # Direct paste
                img_array[dy:dy+patch_h, dx:dx+patch_w] = source_patch
            
            mask[dy:dy+patch_h, dx:dx+patch_w] = 255

        return Image.fromarray(img_array), mask

    @staticmethod
    def object_removal(
        image: Image.Image,
        region: Tuple[int, int, int, int],
        inpainting_method: str = "telea",
        inpaint_radius: int = 3
    ) -> Tuple[Image.Image, np.ndarray]:
        """
        Perform object removal using inpainting with controlled diversity.

        Args:
            image: Source image
            region: (x, y, width, height) of region to remove
            inpainting_method: Method to use ("telea" or "ns")
            inpaint_radius: Radius for inpainting algorithm

        Returns:
            Tuple of (manipulated image, mask)
        """
        img_array = np.array(image)
        mask = np.zeros((image.height, image.width), dtype=np.uint8)

        x, y, w, h = region
        
        # Ensure region is within bounds
        w = min(w, image.width - x)
        h = min(h, image.height - y)
        
        # Mark region in mask
        mask[y:y+h, x:x+w] = 255

        # Inpainting using OpenCV with method selection
        if inpainting_method == "telea":
            inpainted = cv2.inpaint(img_array, mask, inpaint_radius, cv2.INPAINT_TELEA)
        elif inpainting_method == "ns":
            inpainted = cv2.inpaint(img_array, mask, inpaint_radius, cv2.INPAINT_NS)
        else:
            # Default to telea
            inpainted = cv2.inpaint(img_array, mask, inpaint_radius, cv2.INPAINT_TELEA)

        return Image.fromarray(inpainted), mask

    @staticmethod
    def object_insertion(
        image: Image.Image,
        donor_image: Image.Image,
        donor_region: Tuple[int, int, int, int],
        dest_region: Tuple[int, int, int, int],
        scale: float = 1.0,
        rotation: int = 0,
        blend: float = 0.0
    ) -> Tuple[Image.Image, np.ndarray]:
        """
        Perform object insertion from donor image with controlled diversity.

        Args:
            image: Target image
            donor_image: Donor image
            donor_region: (x, y, width, height) of region to extract from donor
            dest_region: (x, y, width, height) of destination in target
            scale: Scale factor
            rotation: Rotation angle in degrees
            blend: Blending strength (0-1)

        Returns:
            Tuple of (manipulated image, mask)
        """
        img_array = np.array(image)
        donor_array = np.array(donor_image)
        mask = np.zeros((image.height, image.width), dtype=np.uint8)

        # Extract donor region
        dx_donor, dy_donor, dw_donor, dh_donor = donor_region
        donor_patch = donor_array[dy_donor:dy_donor+dh_donor, dx_donor:dx_donor+dw_donor].copy()

        # Apply transformations
        if rotation != 0:
            M = cv2.getRotationMatrix2D((dw_donor//2, dh_donor//2), rotation, 1.0)
            donor_patch = cv2.warpAffine(donor_patch, M, (dw_donor, dh_donor))

        if scale != 1.0:
            new_w = int(dw_donor * scale)
            new_h = int(dh_donor * scale)
            donor_patch = cv2.resize(donor_patch, (new_w, new_h))

        # Destination region
        dx_dest, dy_dest, dw_dest, dh_dest = dest_region
        patch_h, patch_w = donor_patch.shape[:2]

        # Ensure patch fits in destination
        actual_dw = max(patch_w, dw_dest)
        actual_dh = max(patch_h, dh_dest)
        
        # Ensure destination is within image bounds
        if dx_dest + actual_dw > image.width:
            actual_dw = image.width - dx_dest
        if dy_dest + actual_dh > image.height:
            actual_dh = image.height - dy_dest
        
        # Resize patch to fit if needed
        if patch_w > actual_dw or patch_h > actual_dh:
            donor_patch = cv2.resize(donor_patch, (actual_dw, actual_dh))
            patch_h, patch_w = donor_patch.shape[:2]

        # Paste with optional blending
        if patch_h > 0 and patch_w > 0:
            if blend > 0:
                # Simple alpha blending at edges
                blended_patch = donor_patch.copy()
                edge_width = max(1, int(min(patch_w, patch_h) * 0.1))
                
                if edge_width < patch_h:
                    blended_patch[:edge_width, :] = (
                        blended_patch[:edge_width, :] * (1 - blend) + 
                        img_array[dy_dest:dy_dest+edge_width, dx_dest:dx_dest+patch_w] * blend
                    ).astype(np.uint8)
                    blended_patch[-edge_width:, :] = (
                        blended_patch[-edge_width:, :] * (1 - blend) + 
                        img_array[dy_dest+patch_h-edge_width:dy_dest+patch_h, dx_dest:dx_dest+patch_w] * blend
                    ).astype(np.uint8)
                if edge_width < patch_w:
                    blended_patch[:, :edge_width] = (
                        blended_patch[:, :edge_width] * (1 - blend) + 
                        img_array[dy_dest:dy_dest+patch_h, dx_dest:dx_dest+edge_width] * blend
                    ).astype(np.uint8)
                    blended_patch[:, -edge_width:] = (
                        blended_patch[:, -edge_width:] * (1 - blend) + 
                        img_array[dy_dest:dy_dest+patch_h, dx_dest+patch_w-edge_width:dx_dest+patch_w] * blend
                    ).astype(np.uint8)
                
                img_array[dy_dest:dy_dest+patch_h, dx_dest:dx_dest+patch_w] = blended_patch
            else:
                # Direct paste
                img_array[dy_dest:dy_dest+patch_h, dx_dest:dx_dest+patch_w] = donor_patch
            
            mask[dy_dest:dy_dest+patch_h, dx_dest:dx_dest+patch_w] = 255

        return Image.fromarray(img_array), mask

    @staticmethod
    def splicing(
        target_image: Image.Image,
        donor_image: Image.Image,
        target_region: Tuple[int, int, int, int],
        donor_region: Tuple[int, int, int, int] = None,
        rotation: int = 0,
        scale: float = 1.0,
        blend: float = 0.0
    ) -> Tuple[Image.Image, np.ndarray]:
        """
        Perform splicing from donor to target with controlled diversity.

        Args:
            target_image: Target image
            donor_image: Donor image
            target_region: (x, y, width, height) in target
            donor_region: (x, y, width, height) in donor (optional)
            rotation: Rotation angle in degrees
            scale: Scale factor
            blend: Blending strength (0-1)

        Returns:
            Tuple of (manipulated image, mask)
        """
        target_array = np.array(target_image)
        donor_array = np.array(donor_image)
        mask = np.zeros((target_image.height, target_image.width), dtype=np.uint8)

        tx, ty, tw, th = target_region

        # If donor region not specified, use center of donor
        if donor_region is None:
            donor_region = (
                (donor_image.width - tw) // 2,
                (donor_image.height - th) // 2,
                tw, th
            )

        dx, dy, dw, dh = donor_region
        donor_patch = donor_array[dy:dy+dh, dx:dx+dw].copy()

        # Apply transformations
        if rotation != 0:
            M = cv2.getRotationMatrix2D((dw//2, dh//2), rotation, 1.0)
            donor_patch = cv2.warpAffine(donor_patch, M, (dw, dh))

        if scale != 1.0:
            new_w = int(dw * scale)
            new_h = int(dh * scale)
            donor_patch = cv2.resize(donor_patch, (new_w, new_h))

        # Resize to fit target region if needed
        patch_h, patch_w = donor_patch.shape[:2]
        if (patch_w, patch_h) != (tw, th):
            donor_patch = cv2.resize(donor_patch, (tw, th))
            patch_h, patch_w = donor_patch.shape[:2]

        # Ensure target region is within bounds
        actual_tw = max(patch_w, tw)
        actual_th = max(patch_h, th)
        
        if tx + actual_tw > target_image.width:
            actual_tw = target_image.width - tx
        if ty + actual_th > target_image.height:
            actual_th = target_image.height - ty
        
        # Resize patch to fit if needed
        if patch_w > actual_tw or patch_h > actual_th:
            donor_patch = cv2.resize(donor_patch, (actual_tw, actual_th))
            patch_h, patch_w = donor_patch.shape[:2]

        # Paste with optional blending
        if patch_h > 0 and patch_w > 0:
            if blend > 0:
                # Simple alpha blending at edges
                blended_patch = donor_patch.copy()
                edge_width = max(1, int(min(patch_w, patch_h) * 0.1))
                
                if edge_width < patch_h:
                    blended_patch[:edge_width, :] = (
                        blended_patch[:edge_width, :] * (1 - blend) + 
                        target_array[ty:ty+edge_width, tx:tx+patch_w] * blend
                    ).astype(np.uint8)
                    blended_patch[-edge_width:, :] = (
                        blended_patch[-edge_width:, :] * (1 - blend) + 
                        target_array[ty+patch_h-edge_width:ty+patch_h, tx:tx+patch_w] * blend
                    ).astype(np.uint8)
                if edge_width < patch_w:
                    blended_patch[:, :edge_width] = (
                        blended_patch[:, :edge_width] * (1 - blend) + 
                        target_array[ty:ty+patch_h, tx:tx+edge_width] * blend
                    ).astype(np.uint8)
                    blended_patch[:, -edge_width:] = (
                        blended_patch[:, -edge_width:] * (1 - blend) + 
                        target_array[ty:ty+patch_h, tx+patch_w-edge_width:tx+patch_w] * blend
                    ).astype(np.uint8)
                
                target_array[ty:ty+patch_h, tx:tx+patch_w] = blended_patch
            else:
                # Direct paste
                target_array[ty:ty+patch_h, tx:tx+patch_w] = donor_patch
            
            mask[ty:ty+patch_h, tx:tx+patch_w] = 255

        return Image.fromarray(target_array), mask


def compute_manipulation_area_ratio(mask: np.ndarray) -> float:
    """
    Compute the ratio of manipulated pixels to total pixels in a mask.
    
    Args:
        mask: Mask array
        
    Returns:
        Ratio of manipulated pixels (0.0 to 1.0)
    """
    manipulated_pixels = np.count_nonzero(mask)
    total_pixels = mask.size
    
    if total_pixels == 0:
        return 0.0
    
    return manipulated_pixels / total_pixels
