FROM joyzoursky/python-chromedriver:3.8


# Устанавливаем Python-библиотеки
WORKDIR /checker

COPY . .

RUN pip install --no-cache-dir -r requirements.txt


# Запуск основного скрипта
CMD ["python", "checker.py"]