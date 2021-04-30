cd /home/grayson/songs-in-common/
source env/bin/activate
git pull
cd songs_in_common
python manage.py migrate
python manage.py collectstatic
sudo systemctl restart gunicorn-songs-in-common
