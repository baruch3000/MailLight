#!/bin/bash

# 1. התקנת חבילת ה-QR
pip install qrcode[pil] --break-system-packages

# 2. ביטול החלון המעצבן ששואל "האם להריץ?" כשלוחצים על האייקון
mkdir -p /home/baruch/.config/pcmanfm/LXDE-pi/
cat <<EOF > /home/baruch/.config/pcmanfm/LXDE-pi/pcmanfm.conf
[ui]
quick_exec=1
EOF

# 3. יצירת אייקון אמיתי ותקין
cat <<EOF > /home/baruch/Desktop/MailLight_App.desktop
[Desktop Entry]
Name=MailLight
Exec=/home/baruch/Desktop/MailLight/launch_kiosk.sh
Type=Application
Terminal=false
Icon=terminal
EOF

# 4. מתן הרשאות הפעלה
chmod +x /home/baruch/Desktop/MailLight_App.desktop

# 5. הגדרת הפעלה אוטומטית בחשמל
mkdir -p /home/baruch/.config/autostart
cp /home/baruch/Desktop/MailLight_App.desktop /home/baruch/.config/autostart/

echo "ההתקנה הושלמה בהצלחה! נא להפעיל מחדש את המכשיר."
