---
name: Android OEM Issue Researcher
description: This skill should be used when the user asks to "research Android OEM issues", "solve Android software problem", "search AOSP documentation", "find Android customized bug solutions", or needs to investigate OEM Android software issues by searching technical knowledge on AOSP webpage CDN or other professional developer forums.
version: 0.1.0
---

# Android OEM Issue Researcher

This skill guides the process of researching and solving OEM (Original Equipment Manufacturer) Android software issues. It ensures that technical searches are directed towards authoritative sources like the Android Open Source Project (AOSP), official CDN, and professional developer forums.

## Core Sources

When investigating Android OEM issues, prioritize searching the following domains:
1. **AOSP Source and Documentation**:
   - `source.android.com` (AOSP Documentation)
   - `cs.android.com` (Android Code Search)
   - `developer.android.com` (Android Developer Documentation)
2. **Professional Forums and Communities**:
   - `stackoverflow.com`
   - `xda-developers.com` (for OEM-specific mods and issues)
   - `issuetracker.google.com` (Android Issue Tracker)

## Workflow Instructions

To research an OEM Android software issue, follow these steps:

1. **Analyze the Issue**:
   Identify the core Android components involved (e.g., SurfaceFlinger, AudioFlinger, Connectivity, PowerManager).
2. **Search Official Documentation**:
   Use web search tools with domain filters to find official AOSP architectural documentation or implementation guidelines.
   Example: `site:source.android.com SurfaceFlinger vs OEM modification`
3. **Search Issue Trackers and Forums**:
   Search Google Issue Tracker or StackOverflow for similar bug reports and developer discussions.
   Example: `site:issuetracker.google.com [issue description]`
4. **Code Search (if applicable)**:
   If needing to look at pure AOSP implementation to compare with an OEM's issue, refer to `cs.android.com` for the exact Android version.
5. **Synthesize Findings**:
   Provide the solution or technical context, clearly citing the AOSP documentation or forum threads where the information was found. Focus on deep technical explanations over high-level summaries.

## Best Practices
- Always verify the Android OS version since AOSP architecture changes significantly between versions (e.g., Android 13 vs 14).
- Distinguish between AOSP native behavior and potential OEM customizations (like Samsung OneUI, Xiaomi MIUI, etc.).
- When providing code or configuration fixes, cite the specific AOSP path (e.g., `frameworks/base/services/core/...`).
