
try:
    import copilotkit
    print("copilotkit version:", getattr(copilotkit, "__version__", "unknown"))
    print("copilotkit attributes:", dir(copilotkit))
except ImportError:
    print("copilotkit not installed")

try:
    import ag_ui_langgraph
    print("ag_ui_langgraph attributes:", dir(ag_ui_langgraph))
except ImportError:
    print("ag_ui_langgraph not installed")
