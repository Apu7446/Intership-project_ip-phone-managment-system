# SBAC Bank PLC — IP Phone Management System

A desktop management application for managing internal IP phone directories, branch contacts, head office departments, and user access for SBAC Bank PLC.

## Features

- **Directory & Contact Search**: Instant search and filtering of employee extensions, designations, and department contacts.
- **Head Office & Branch Organization**: Categorized views for Head Office divisions and Branch/Sub-Branch networks across the country.
- **Role-based Authentication**: Secure user management with role-based permissions (Admin, User).
- **Import / Export**: Bulk data import from Excel/CSV files (`Branch & Sub-Branch.csv`, `HeadOffice.csv`).
- **Automated Database Backups**: Scheduled and on-demand MySQL database backups with retention management.
- **Modern User Interface**: Built using CustomTkinter with SBAC Bank's official corporate color palette.

## Tech Stack

- **Python 3.10+**
- **CustomTkinter & Tkinter** (Modern GUI components)
- **MySQL Connector / MariaDB** (Database layer)
- **Pillow** (Image and asset handling)
- **openpyxl** (Excel spreadsheet processing)

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Apu7446/Intership-project_ip-phone-managment-system.git
cd Intership-project_ip-phone-managment-system
```

### 2. Quick Launch (Windows)
Double-click `RUN_APP.bat`. The launcher script will automatically:
- Verify your Python installation
- Create a local virtual environment (`venv`) if not already present
- Install the required dependencies from `requirements.txt`
- Create a desktop shortcut with the official app icon
- Launch the application

### 3. Manual Installation
If you prefer running manually with Python:
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

### 4. Database Setup
1. Ensure MySQL Server is running.
2. Initialize database schema:
   ```bash
   mysql -u root -p < schema.sql
   ```
   Or run the included interactive setup script:
   ```bash
   python setup_server.py
   ```
3. Configure database connection parameters in `server_config.json`.
