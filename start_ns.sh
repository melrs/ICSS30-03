find "$(dirname "$0")" -maxdepth 1 -type f -name 'application_*.log' -delete
pyro5-ns -n localhost
