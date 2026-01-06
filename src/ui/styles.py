"""
Global UI Styles (QSS)
"""

def get_main_stylesheet():
    """Return the main QSS stylesheet for the application"""
    return """
    /* Main Window */
    QMainWindow {
        background-color: #1a1c23; /* Dark Pro Background */
        color: #e0e0e0;
    }
    QWidget {
        color: #e0e0e0;
        font-family: 'Segoe UI', 'Inter', system-ui, sans-serif;
        font-size: 13px;
    }
    
    /* Tables (Library) */
    QTableView {
        background-color: #121212;
        alternate-background-color: #1b1b1b;
        border: 1px solid #2d303b;
        border-radius: 8px;
        gridline-color: transparent;
        selection-background-color: #00d1b2; /* Cyan Accent */
        selection-color: #000000;
        outline: none;
    }
    QTableView::item {
        padding: 4px;
        border-bottom: 1px solid #1a1a1a;
    }
    QTableView::item:selected {
        border-radius: 4px;
    }
    
    /* Headers */
    QHeaderView::section {
        background-color: #24262d;
        color: #a0a0a0;
        text-transform: uppercase;
        font-weight: bold;
        font-size: 11px;
        border: none;
        padding: 8px;
        border-bottom: 1px solid #333;
    }
    QHeaderView::section:first {
        border-top-left-radius: 8px;
    }
    QHeaderView::section:last {
        border-top-right-radius: 8px;
    }
    
    /* Sidebar Tree */
    QTreeWidget {
        background-color: #24262d;
        border: 1px solid #2d303b; /* Outer border is fine */
        border-radius: 8px;
        outline: none;
        padding: 4px;
    }
    QTreeWidget::item {
        padding: 4px 8px; /* Reduced vertical padding */
        margin: 2px 6px;  /* Increased side margin to shrink the hover box */
        border: none; 
        border-radius: 4px;
        color: #e0e0e0;
    }
    QTreeWidget::branch {
        background: transparent;
        border: none;
    }
    QTreeWidget::branch:has-children:!has-siblings:closed,
    QTreeWidget::branch:closed:has-children:has-siblings {
        border-image: none;
        image: none; /* Let system draw arrow, or specify one if needed. System usually fine if background is transparent */
    }
    QTreeWidget::item:hover {
        background-color: #333642;
        color: #ffffff;
        border: none;
    }
    
    /* Buttons */
    QPushButton {
        background-color: #333;
        border: 1px solid #444;
        border-radius: 6px;
        padding: 6px 14px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #444;
        border-color: #555;
    }
    QPushButton:pressed {
        background-color: #00d1b2;
        color: #000;
        border-color: #00d1b2;
    }
    QPushButton:disabled {
        background-color: #222;
        color: #555;
        border-color: #333;
    }
    
    /* Scrollbars (Modern Slate) */
    QScrollBar:vertical {
        border: none;
        background: #1a1c23;
        width: 10px;
        margin: 0px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #3a3d4a;
        min-height: 30px;
        border-radius: 5px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover {
        background: #4a4d5a;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        border: none;
        background: #1a1c23;
        height: 10px;
        margin: 0px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal {
        background: #3a3d4a;
        min-width: 30px;
        border-radius: 5px;
        margin: 2px;
    }
    
    /* Tooltips */
    QToolTip {
        background-color: #111;
        color: #fff;
        border: 1px solid #333;
        border-radius: 4px;
        padding: 4px;
    }
    
    /* Dialogs */
    QDialog {
        background-color: #1a1c23;
    }
    QLineEdit {
        background-color: #121212;
        border: 1px solid #333;
        border-radius: 4px;
        padding: 6px;
        color: #fff;
    }
    QLineEdit:focus {
        border-color: #00d1b2;
    }
    QCheckBox {
        color: #e0e0e0;
    }
    """
