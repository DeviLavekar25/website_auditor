import gradio as gr
import asyncio
from auditor import audit_website, summarize_audit

def run_audit(url):
    # Run the audit and get result
    result = asyncio.run(audit_website(url))
    
    # Generate summary
    summary = asyncio.run(summarize_audit(
        result['title'],
        result['description'],
        result['num_links'],
        result['speed'],
        result['seo'],
        result['accessibility']
    ))

    # Format output
    output = f"""
📄 Title: {result.get('title', 'N/A')}
📝 Description: {result.get('description', 'Not found')}
🔗 Links Found: {result.get('num_links', 0)}
🚀 DOMContentLoaded: {result.get('speed', {}).get('domContentLoaded', 'N/A')} ms
⚡ Load Event: {result.get('speed', {}).get('loadEvent', 'N/A')} ms

🔍 SEO Tags:
- Title Tag: {"✅" if result.get('seo', {}).get('title') else "❌"}
- Meta Description: {"✅" if result.get('seo', {}).get('meta') else "❌"}
- Canonical Tag: {"✅" if result.get('seo', {}).get('canonical') else "❌"}

🧩 Accessibility (ARIA roles): {result.get('access', {}).get('aria_roles', 'N/A')}

📋 Summary:
{summary}
"""
    return output

# Launch Gradio interface
gr.Interface(
    fn=run_audit,
    inputs=gr.Textbox(label="Enter Website URL (e.g. https://example.com)"),
    outputs=gr.Textbox(label="Audit Report", lines=20),
    title="🌐 Website Auditor Bot",
    description="Enter a website URL to perform an SEO, performance, and accessibility audit.",
    theme="default"
).launch()
