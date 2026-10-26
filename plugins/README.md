JARVIS Plugin SDK

Create plugins/<plugin-id>/manifest.json with name, version, description, author, and permissions fields. Use plugins list and plugins validate to inspect metadata. JARVIS deliberately does not import or execute arbitrary plugin Python code: Python plugins are not sandboxed by the OS. Review source and define permissions before adding executable integrations. Never store secrets in plugin manifests.
