#!/bin/bash
# התקנת ספריות נדרשות
pip install qrcode[pil] --break-system-packages

# יצירת אייקון בשולחן העבודה
cat <<EOF > /home/baruch/Desktop/MailLight_App.desktop
[Desktop Entry]
Name=MailLight
Exec=/home/baruch/Desktop/MailLight/launch_kiosk.sh
Type=Application
Terminal=false
EOF
chmod +x /home/baruch/Desktop/MailLight_App.desktop

# הגדרת הפעלה אוטומטית בהדלקה
mkdir -p /home/baruch/.config/autostart
cp /home/baruch/Desktop/MailLight_App.desktop /home/baruch/.config/autostart/

echo "הכל הוגדר בהצלחה!"
