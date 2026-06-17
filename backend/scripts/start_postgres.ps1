# تشغيل خادم PostgreSQL المحمول (التطوير المحلي على ويندوز)
# الاستخدام:  powershell -ExecutionPolicy Bypass -File scripts\start_postgres.ps1
$bin  = "C:\Users\mahmo\pg16\pgsql\bin"
$data = "C:\Users\mahmo\pgdata16"
& "$bin\pg_ctl.exe" -D $data -l "$data\server.log" -o "-p 5432" -w start
$env:PGPASSWORD = "postgres"
& "$bin\psql.exe" -U postgres -h localhost -p 5432 -d reshaqa -c "SELECT 'reshaqa ready' AS status;"
