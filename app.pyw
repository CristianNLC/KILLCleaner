import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ui.main_window import CleanerWindow

def main():
    app = CleanerWindow()
    app.mainloop()

if __name__ == "__main__":
    main()