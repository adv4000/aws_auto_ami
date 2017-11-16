# BackUp EC2 to AMI
AWS AutoCreate AMI and delete old ones. EC2 Backups.

Python Script looking for EC2 with
  Tag = Name
  Value = SERVER_NAME
and create AMI
Also checking for old AMI with same Tag/Value, Deregister them if they older than X days and delete associated disk snapshots.

Simple solution for EC2 Backup.

Set this script as cron job in Linux or scheduled task in Windows.
