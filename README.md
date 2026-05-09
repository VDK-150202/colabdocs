python3 -m venv venv 
.\venv\Scripts\activate    
django-admin startproject collabdocs . 
python manage.py startapp users ./apps/users    
python manage.py startapp workspaces ./apps/workspaces
python manage.py startapp documents ./apps/documents