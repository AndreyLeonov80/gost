# gost
**ИИ для работы с рассуждениями и QA по ГОСТам**

**Задача** https://habr.com/ru/companies/omk-it/articles/850434/

**Верхнеуровневая текущая и стратегическая "Архитекура ИИ решения"**

![Архитектура ИИ решения](https://raw.githubusercontent.com/AndreyLeonov80/gost/refs/heads/main/back/architecture/%D0%92%D0%B5%D1%80%D1%85%D0%BD%D0%B5%D1%83%D1%80%D0%BE%D0%B2%D0%BD%D0%B5%D0%B2%D0%B0%D1%8F%20%D1%82%D0%B5%D0%BA%D1%83%D1%89%D0%B0%D1%8F%20%D0%B8%20%D1%81%D1%82%D1%80%D0%B0%D1%82%D0%B5%D0%B3%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B0%D1%8F%20%22%D0%90%D1%80%D1%85%D0%B8%D1%82%D0%B5%D0%BA%D1%83%D1%80%D0%B0%20%D0%98%D0%98%20%D1%80%D0%B5%D1%88%D0%B5%D0%BD%D0%B8%D1%8F%22.png)

**Методология на примере ГОСТ 14637-89.pdf.**

1. Сегментация и очистка PDF-файла

       Разделение документа на информационные блоки и таблицы.
       Очистка данных от лишней информации.
       Результат сохраняется в: gost/back/py/datasource/infoblocks/ГОСТ 14637-89 - null.txt

2. Генерация пакета QA через LLM и промт-инжиниринг
        
       Файлы находятся в директории: gost/back/py/datasource

4. Обучение модели 

   Выполнить
  
       pip install -r requirements.txt
   
   В gost/back/py/train.py
  
       указать путь с json файлами base_path = 'gost/back/py'
       указать модель обучения которая сохранится в файл self.model_path = 'trained_model.pkl' (или trained_model_promt_template.pkl)

   Запустить gost/back/py/train.py для обучения модели на основе QA данных
	
       логи
       qa_model_20241030_115625.log для модели trained_model.pkl
       trained_model_promt_template.pkl.log для модели trained_model_promt_template.pkl (или trained_model_promt_template.pkl)

4. Проверяем модель на copilot gost/back/py/copilot.py
   
       указать путь для pkl модели base_path = 'gost/back/py'
       указать pkl модель self.model_path = 'trained_model.pkl' (или trained_model_promt_template.pkl)

**Варианты LLM:**
  - платные api gpt4 https://platform.openai.com/docs/concepts
  - платные api claude https://docs.anthropic.com/en/home
  - платные c большим выбором моделей без своего GPU https://openrouter.ai
  - локальные LLM например через сервер настроенный в https://lmstudio.ai
  - аренда gpu например https://immers.cloud

Тюнинг параметров LLM от которых зависити результат - могу описать по запросу.

**Демо-сервер на Flutter:**
     
Приложение: https://appomk.frontback.tech

Видео демонстрация: https://cloud.mail.ru/public/K75R/Rc9Jq5pGZ

Модели и результаты:
- **trained_model.pkl** (обучена на **ГОСТ 14637-89.pdf** через гиперсегментацию ГОСТа на инфоблоки/таблицы)
  
  Видео https://cloud.mail.ru/public/jSCk/txkSYpVw7

      промт gost/back/py/datasource/infoblocks/promts.txt
      QA обучающая выборка:
       - gost/back/py/datasource/infoblocks
       - gost/back/py/datasource/tables

- **trained_model_promt_template.pkl** (обучена на **ГОСТ 14637-89.pdf** через вариации промта "Какие границы для испытания на временное сопротивление для широкополосного проката, марка стали Ст3сп, толщина проката 20, категория 5 для ГОСТ 14637-89?")
    
      промт gost/back/py/datasource/infoblocks2/gen-llm plk promt.txt
      QA обучающая выборка gost/back/py/datasource/infoblocks2/89-1.json

Алгоритмы/технологии которые есть в запасе и которые можно отдельно обсудить:
- матчинг вопросов и в целом матчинг терминов
- распознавание таблиц и ячеек таблиц, если они являются графическими элементами 
- оптимизации алгоритмов
- ИИ copilot по ГОСТам для документооборота в структурах сделок
- openapi backend api
- другие

**Контакты:**

andrey.leonov@bimeister.com

https://t.me/aidialog

**О архитекторе и разработчике:**

https://codeboost.ru/about