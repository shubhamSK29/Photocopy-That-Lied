import streamlit as st
import requests
import io
from PIL import Image
import pandas as pd
import time

# Page configuration
st.set_page_config(
    page_title="Photocopy That Lied",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
    }
    .coverage-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #17a2b8;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def check_api_health():
    """Check if the backend API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        return response.status_code == 200, response.json()
    except requests.exceptions.RequestException:
        return False, None

def get_config():
    """Get configuration from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/config", timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        pass
    return None

def analyze_image(file):
    """Analyze uploaded image"""
    try:
        # Read file content
        file_content = file.read()
        
        st.info(f"Debug: File size: {len(file_content)} bytes, File type: {file.type}")
        
        # Create files dict with proper multipart form data
        files = {
            'file': (file.name, file_content, file.type)
        }
        
        st.info(f"Debug: Sending request to {API_BASE_URL}/api/analyze")
        
        response = requests.post(f"{API_BASE_URL}/api/analyze", files=files, timeout=30)
        
        st.info(f"Debug: Response status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API returned error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error analyzing image: {str(e)}")
        return None

def get_analysis(analysis_id):
    """Get analysis results"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/analysis/{analysis_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None

def get_artifact(analysis_id, artifact_name):
    """Get artifact image"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/artifacts/{analysis_id}/{artifact_name}", timeout=10)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
    except requests.exceptions.RequestException:
        return None

def get_report(analysis_id, format='json'):
    """Get report in specified format"""
    try:
        params = {'format': format} if format != 'json' else {}
        response = requests.get(f"{API_BASE_URL}/api/report/{analysis_id}", params=params, timeout=10)
        if response.status_code == 200:
            if format == 'json':
                return response.json()
            else:
                return response.content
    except requests.exceptions.RequestException:
        return None

# Main application
def main():
    # Header
    st.markdown('<div class="main-header">🔍 PHOTOCOPY THAT LIED</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-Assisted Image Forensics for Crop Insurance Review</div>', unsafe_allow_html=True)
    
    # Check API health
    api_healthy, health_data = check_api_health()
    
    if not api_healthy:
        st.error("⚠️ Backend API is not running. Please start the backend server first:")
        st.code(".venv\\Scripts\\uvicorn backend.main:app --port 8000", language="powershell")
        st.info("Once the backend is running, refresh this page to continue.")
        return
    
    # Display API status
    with st.sidebar:
        st.subheader("🖥️ System Status")
        st.success("✅ Backend API Connected")
        if health_data:
            st.json(health_data)
        
        st.subheader("📋 Supported Formats")
        config = get_config()
        if config:
            st.write(f"**Max File Size:** {config.get('max_file_size_mb', 25)} MB")
            st.write(f"**Formats:** {', '.join(config.get('allowed_formats', ['JPEG', 'PNG', 'WEBP']))}")
        else:
            st.write("JPEG, PNG, WEBP")
            st.write("Max size: 25 MB")
        
        st.subheader("⚠️ Important Notes")
        st.info("""
        - **Manipulation Evidence ≠ Fraud Probability**
        - **Data Coverage is separate from Manipulation Evidence**
        - Missing EXIF/compression ≠ proof of manipulation
        - Demo mode clearly labelled when active
        """)

    # Auto-refresh for live changes
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh results", value=False)
    if auto_refresh:
        st.sidebar.write("Results will refresh every 5 seconds")
        time.sleep(5)
        st.rerun()

    # File upload section
    st.header("📤 Upload Image for Analysis")
    
    # Quick test with dataset image
    col1, col2 = st.columns([2, 1])
    with col2:
        if st.button("🧪 Test with Sample Image"):
            # Use a sample image from the dataset
            sample_image_path = "dataset/authentic/phoneA_flagship_000_original.jpg"
            try:
                with open(sample_image_path, 'rb') as f:
                    sample_file = io.BytesIO(f.read())
                    sample_file.name = "phoneA_flagship_000_original.jpg"
                    sample_file.type = "image/jpeg"
                    st.session_state.uploaded_sample = sample_file
                    st.success("Sample image loaded! Click 'Analyze Image' to process it.")
            except FileNotFoundError:
                st.error("Sample image not found. Please upload your own image.")
    
    uploaded_file = st.file_uploader(
        "Choose an image file",
        type=['jpg', 'jpeg', 'png', 'webp'],
        help="Upload a JPEG, PNG, or WebP image for forensic analysis"
    )
    
    # Use sample image if loaded
    if 'uploaded_sample' in st.session_state and uploaded_file is None:
        uploaded_file = st.session_state.uploaded_sample
    
    if uploaded_file:
        # Reset file pointer to beginning
        uploaded_file.seek(0)
        
        # Display uploaded image
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("📷 Uploaded Image")
            image = Image.open(uploaded_file)
            st.image(image, width='stretch')
        
        with col2:
            st.subheader("📊 Image Information")
            st.write(f"**Filename:** {uploaded_file.name}")
            st.write(f"**File Size:** {uploaded_file.size / 1024:.2f} KB")
            st.write(f"**Dimensions:** {image.size[0]} x {image.size[1]} pixels")
            st.write(f"**Format:** {image.format}")
            st.write(f"**MIME Type:** {uploaded_file.type}")
        
        # Analyze button
        if st.button("🔍 Analyze Image", type="primary"):
            # Reset file pointer again before reading
            uploaded_file.seek(0)
            
            with st.spinner("Analyzing image... This may take a few seconds..."):
                result = analyze_image(uploaded_file)
                
                if result:
                    st.success("✅ Analysis completed successfully!")
                    st.session_state.analysis_id = result.get('analysis_id')
                    st.session_state.analysis_result = result
                else:
                    st.error("❌ Analysis failed. Please try again.")
    
    # Display analysis results
    if 'analysis_id' in st.session_state:
        st.divider()
        st.header("📈 Analysis Results")
        
        # Get full analysis details
        analysis_id = st.session_state.analysis_id
        analysis_data = get_analysis(analysis_id)
        
        if analysis_data:
            # Main scores
            col1, col2 = st.columns(2)
            
            with col1:
                manipulation_evidence = analysis_data.get('manipulation_evidence', 0)
                color = '#dc3545' if manipulation_evidence > 60 else '#ffc107' if manipulation_evidence > 30 else '#28a745'
                st.markdown(f"""
                <div class="score-card" style="background: linear-gradient(135deg, {color} 0%, #667eea 100%);">
                    <h3>MANIPULATION EVIDENCE</h3>
                    <h1>{manipulation_evidence:.1f}%</h1>
                    <p>Risk Band: {analysis_data.get('risk_band', 'Unknown')}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                data_coverage = analysis_data.get('data_coverage', 0)
                st.markdown(f"""
                <div class="coverage-card">
                    <h3>DATA COVERAGE</h3>
                    <h1>{data_coverage:.1f}%</h1>
                    <p>Analysis Confidence</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Demo mode indicator
            fusion_data = analysis_data.get('fusion', {})
            if fusion_data.get('demo_mode', False):
                st.markdown('<div class="warning-box">⚠️ <strong>DEMO FALLBACK MODE</strong> - Using deterministic rule fusion (not calibrated ML model)</div>', unsafe_allow_html=True)
            
            # Detector results
            st.subheader("🔬 Detector Results")
            detectors = analysis_data.get('detectors', {})
            
            for detector_name, detector_data in detectors.items():
                with st.expander(f"{detector_name.replace('_', ' ').title()}"):
                    st.write(f"**Status:** {detector_data.get('status', 'Unknown')}")
                    st.write(f"**Score:** {detector_data.get('score', 0):.3f}")
                    st.write(f"**Explanation:** {detector_data.get('explanation', 'No explanation provided')}")
            
            # Heatmap display
            st.subheader("🌡️ Visual Analysis")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**Original**")
                original_img = get_artifact(analysis_id, 'original.png')
                if original_img:
                    st.image(original_img, width='stretch')
            
            with col2:
                st.write("**Heatmap**")
                heatmap_img = get_artifact(analysis_id, 'heatmap.png')
                if heatmap_img:
                    st.image(heatmap_img, width='stretch')
            
            with col3:
                st.write("**Overlay**")
                overlay_img = get_artifact(analysis_id, 'overlay.png')
                if overlay_img:
                    st.image(overlay_img, width='stretch')
            
            # Provenance information
            st.subheader("🔗 Provenance Information")
            image_data = analysis_data.get('image', {})
            metadata_data = analysis_data.get('metadata', {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Analysis ID:** {analysis_id}")
                st.write(f"**SHA-256:** {image_data.get('sha256', 'N/A')}")
                st.write(f"**File Type:** {image_data.get('format', 'N/A')}")
            
            with col2:
                st.write(f"**Dimensions:** {image_data.get('width', 0)} x {image_data.get('height', 0)}")
                st.write(f"**File Size:** {image_data.get('file_size', 0) / 1024:.2f} KB")
                st.write(f"**EXIF Present:** {metadata_data.get('exif_present', False)}")
            
            # Warnings and limitations
            if analysis_data.get('warnings') or analysis_data.get('limitations'):
                st.subheader("⚠️ Warnings & Limitations")
                
                if analysis_data.get('warnings'):
                    for warning in analysis_data.get('warnings', []):
                        st.markdown(f'<div class="warning-box">⚠️ {warning}</div>', unsafe_allow_html=True)
                
                if analysis_data.get('limitations'):
                    for limitation in analysis_data.get('limitations', []):
                        st.markdown(f'<div class="info-box">ℹ️ {limitation}</div>', unsafe_allow_html=True)
            
            # Disclaimer
            st.subheader("📜 Disclaimer")
            disclaimer = analysis_data.get('disclaimer', 'No disclaimer provided')
            st.info(disclaimer)
            
            # Report download
            st.subheader("📥 Download Reports")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📄 Download JSON Report"):
                    report_data = get_report(analysis_id, 'json')
                    if report_data:
                        st.download_button(
                            label="Download JSON",
                            data=str(report_data),
                            file_name=f"report_{analysis_id}.json",
                            mime="application/json"
                        )
            
            with col2:
                if st.button("🌐 Download HTML Report"):
                    report_data = get_report(analysis_id, 'html')
                    if report_data:
                        st.download_button(
                            label="Download HTML",
                            data=report_data,
                            file_name=f"report_{analysis_id}.html",
                            mime="text/html"
                        )
            
            with col3:
                if st.button("📑 Download PDF Report"):
                    report_data = get_report(analysis_id, 'pdf')
                    if report_data:
                        st.download_button(
                            label="Download PDF",
                            data=report_data,
                            file_name=f"report_{analysis_id}.pdf",
                            mime="application/pdf"
                        )
                    else:
                        st.warning("PDF generation may not be available in this environment")
            
            # New analysis button
            if st.button("🔄 New Analysis"):
                del st.session_state.analysis_id
                del st.session_state.analysis_result
                st.rerun()

if __name__ == "__main__":
    main()
