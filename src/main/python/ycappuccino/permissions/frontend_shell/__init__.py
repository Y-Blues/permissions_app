"""a terminal frontend for permissions_app (login, then change password), built on
ycappuccino-ui/ycappuccino-ui-shell -- two screens loaded from YAML templates
(frontend_shell/screens/), no hand-written per-screen logic, see main.py. Talks to its own backend
through a real IServiceEndpoint (ycappuccino.ui.ycappuccino_transport), never HTTP -- see main.py's
docstring for why."""
