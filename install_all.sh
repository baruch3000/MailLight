#!/bin/bash
# יצירת קובץ הפעלה תקין
cat <<EOF > /home/baruch/Desktop/MailLight_App.desktop
[Desktop Entry]
Name=MailLight
Exec=/home/baruch/Desktop/MailLight/launch_kiosk.sh
Icon=/usr/share/pixmaps/python.xpm
Type=Application
Terminal=false
Categories=Application;
EOF

# מתן אישור הרצה
chmod +x /home/baruch/Desktop/MailLight_App.desktop

# העתקה להפעלה אוטומטית
mkdir -p /home/baruch/.config/autostart
cp /home/baruch/Desktop/MailLight_App.desktop /home/baruch/.config/autostart/
