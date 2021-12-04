@echo off
rem blender.exe must be in your system path
blender.exe --background --factory-startup --python "%~dp0blender-example-cli-cmd.py" -- %*
