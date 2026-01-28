# MAC Risk Summarizer

## Variables
- `mac_address`: The MAC address to analyze

## Prompt

Analyze the device with MAC address: {{mac_address}}

Use the available Armis tools to gather information about this device. Then provide a comprehensive security assessment.

## Required Analysis

1. **Device Details**: Retrieve and summarize:
   - Device type and category
   - Manufacturer
   - Operating system and version
   - First seen and last seen timestamps
   - Network information (IP, VLAN, etc.)

2. **Security Risks**: Identify the top 3 security risks for this device based on:
   - OS version and patch status
   - Device type vulnerabilities
   - Network exposure
   - Behavioral anomalies

3. **Recommendations**: Provide top 3 actionable recommendations to improve security posture.

4. **Overall Risk Evaluation**: Assign a risk level (Low/Medium/High/Critical) with justification.

## Output Format

Structure your response as:

### Device Summary
- Type: [device type]
- Manufacturer: [manufacturer]
- OS: [operating system and version]
- First Seen: [timestamp]
- Last Seen: [timestamp]
- Network: [IP/VLAN info]

### Risk Analysis
1. **[Risk Name]** (Severity: High/Medium/Low)
   - Description of the risk

2. **[Risk Name]** (Severity: High/Medium/Low)
   - Description of the risk

3. **[Risk Name]** (Severity: High/Medium/Low)
   - Description of the risk

### Recommendations
1. [Actionable recommendation]
2. [Actionable recommendation]
3. [Actionable recommendation]

### Overall Assessment
**Risk Level: [Low/Medium/High/Critical]**

[Justification for the risk level based on findings]
