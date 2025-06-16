from cx_Freeze import setup, Executable

setup(
    name="TestApp",
    version="0.1",
    description="A simple test application",
    executables=[Executable("test_window.py", base="Win32GUI")]
)
