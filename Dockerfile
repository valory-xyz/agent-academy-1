FROM python:3.8

COPY . .

CMD ["sh", "-c", "tail -f /dev/null"]