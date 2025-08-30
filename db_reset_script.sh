rm instance/*.db 
rm -rf migrations
flask db init
flask db migrate -m "fresh start"
flask db upgrade
