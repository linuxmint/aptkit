Index: aptdaemon-1.1.1+bzr982/aptdaemon/gtk3widgets.py
===================================================================
--- aptdaemon-1.1.1+bzr982.orig/aptdaemon/gtk3widgets.py
+++ aptdaemon-1.1.1+bzr982/aptdaemon/gtk3widgets.py
@@ -40,6 +40,8 @@ import re
 
 import gi
 gi.require_version("Vte", "2.91")
+gi.require_version("Gdk", "3.0")
+gi.require_version("Gtk", "3.0")
 
 import apt_pkg
 from gi.repository import GObject
