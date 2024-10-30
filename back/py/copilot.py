import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging
import sys
from datetime import datetime
import re
import os
import pickle
from typing import Dict, List, Tuple
from scipy.sparse import issparse
from tabulate import tabulate
from collections import defaultdict

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'qa_model_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


class MaterialsQAModel:
    def __init__(self):
        logger.info("Инициализация модели MaterialsQAModel")
        self.vectorizer = TfidfVectorizer()
        self.questions = []
        self.answers = {}
        self.question_vectors = None
        self.data_sources = {}
        self.failed_questions = []
        self.is_trained = False

        self.model_path = 'trained_model.pkl'
        #self.model_path = 'trained_model_promt_template.pkl'

        logger.info("Модель инициализирована успешно")

    def save_model(self):
        """Сохранение обученной модели в файл"""
        if not self.is_trained:
            logger.warning("Попытка сохранить необученную модель")
            return False

        try:
            model_data = {
                'vectorizer': self.vectorizer,
                'questions': self.questions,
                'answers': self.answers,
                'question_vectors': self.question_vectors,
                'data_sources': self.data_sources,
                'is_trained': self.is_trained
            }

            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)

            logger.info(f"Модель успешно сохранена в {self.model_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при сохранении модели: {str(e)}")
            return False

    def load_model(self) -> bool:
        """Загрузка обученной модели из файла"""
        if not os.path.exists(self.model_path):
            logger.info("Файл модели не найден")
            return False

        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)

            self.vectorizer = model_data['vectorizer']
            self.questions = model_data['questions']
            self.answers = model_data['answers']
            self.question_vectors = model_data['question_vectors']
            self.data_sources = model_data['data_sources']
            self.is_trained = model_data['is_trained']

            logger.info(f"Модель успешно загружена из {self.model_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {str(e)}")
            return False

    def load_all_data(self, base_path: str):
        """Загрузка данных из всех файлов"""
        # Сначала пробуем загрузить сохраненную модель
        if self.load_model():
            logger.info("Использована сохраненная модель")
            return

        logger.info("Начало загрузки данных из всех файлов")

        # Пути к файлам
        table_files = [
            os.path.join(base_path, "datasource/tables", f"89-table{i}.json")
            for i in range(1, 7)
        ]
        infoblock_files = [
            os.path.join(base_path, "datasource/infoblocks", f"89-{i}.json")
            for i in range(1, 7)
        ]

        file_count = 0
        for file_path in table_files + infoblock_files:
            if os.path.exists(file_path):
                source_type = "table" if "table" in file_path else "infoblock"
                self.load_file(file_path, source_type)
                file_count += 1
            else:
                logger.warning(f"Файл не найден: {file_path}")

        logger.info(f"Обработано файлов: {file_count}")
        logger.info(f"Загружено вопросов: {len(self.questions)}")

        if self.questions:
            self.vectorize_questions()
            self.is_trained = True
            # Сохраняем обученную модель
            self.save_model()
        else:
            logger.error("Не загружено ни одного вопроса")
            print("Ошибка: не удалось загрузить вопросы")

    def load_file(self, file_path: str, source_type: str):
        """Загрузка данных из одного файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            file_name = os.path.basename(file_path)
            source_name = f"{source_type.capitalize()} {file_name}"

            loaded_count = 0
            for item in data:
                if 'q' in item and 'a' in item:
                    question = item['q']
                    answer = item['a']

                    self.questions.append(question)
                    self.answers[question] = answer
                    self.data_sources[question] = source_name
                    loaded_count += 1

            logger.info(f"Загружено {loaded_count} записей из {file_name}")

        except Exception as e:
            logger.error(f"Ошибка при загрузке файла {file_path}: {str(e)}")
            print(f"Ошибка при загрузке файла {file_path}: {str(e)}")

    def vectorize_questions(self):
        """Векторизация всех вопросов"""
        if not self.questions:
            logger.error("Нет вопросов для векторизации")
            return

        try:
            logger.info(f"Векторизация {len(self.questions)} вопросов")
            self.question_vectors = self.vectorizer.fit_transform(self.questions)
            logger.info(f"Векторизация завершена. Размер: {self.question_vectors.shape}")
        except Exception as e:
            logger.error(f"Ошибка векторизации: {str(e)}")
            self.question_vectors = None

    def find_similar_questions(self, question: str, top_k: int = 5) -> List[Dict]:
        """Поиск наиболее похожих вопросов"""
        if not self.is_trained or self.question_vectors is None:
            logger.error("Модель не обучена или векторы не инициализированы")
            return []

        try:
            question_vector = self.vectorizer.transform([question])
            similarities = cosine_similarity(question_vector, self.question_vectors).flatten()
            top_indices = similarities.argsort()[-top_k:][::-1]

            similar_questions = []
            for idx in top_indices:
                q = self.questions[idx]
                source = self.data_sources.get(q, "Неизвестный источник")
                if source != "Неизвестный источник":
                    similar_questions.append({
                        'similarity': float(similarities[idx]),
                        'question': q,
                        'answer': self.answers[q],
                        'source': source
                    })

            return similar_questions

        except Exception as e:
            logger.error(f"Ошибка при поиске похожих вопросов: {str(e)}")
            return []

    def generate_answer(self, question: str) -> Tuple[str, float, str]:
        """Генерация ответа на основе похожих вопросов"""
        if not self.is_trained:
            return "Модель не обучена", 0.0, "Ошибка"

        similar_questions = self.find_similar_questions(question, top_k=1)

        if similar_questions:
            most_similar = similar_questions[0]
            if most_similar['similarity'] > 0.5:
                return most_similar['answer'], most_similar['similarity'], most_similar['source']

            logger.warning(f"Низкая уверенность ({most_similar['similarity']:.2f}) для вопроса: {question}")

        return "Не удалось найти подходящий ответ", 0.0, "Неизвестный источник"

    def evaluate_answer(self, generated_answer: str, correct_answer: str) -> bool:
        """Оценка правильности ответа"""
        generated_clean = re.sub(r'\s+', '', generated_answer.lower())
        correct_clean = re.sub(r'\s+', '', correct_answer.lower())
        return generated_clean == correct_clean


def test_model_with_stats(model: MaterialsQAModel) -> Dict:
    """Тестирование модели и сбор статистики"""
    logger.info("Начало тестирования модели")
    print("\nНачало тестирования модели...")

    if not model.is_trained:
        logger.error("Модель не обучена")
        print("Ошибка: модель не обучена")
        return {}

    # Статистика по источникам
    source_stats = defaultdict(lambda: {
        'total': 0,
        'correct': 0,
        'high_conf': 0,  # confidence > 0.8
        'med_conf': 0,  # 0.5 < confidence <= 0.8
        'low_conf': 0,  # confidence <= 0.5
        'avg_confidence': 0.0,
    })

    # Общая статистика
    total_stats = {
        'total_questions': 0,
        'total_correct': 0,
        'total_high_conf': 0,
        'total_med_conf': 0,
        'total_low_conf': 0,
        'avg_confidence': 0.0,
    }

    # Тестирование на всех вопросах
    for question in model.questions:
        answer, confidence, source = model.generate_answer(question)
        correct_answer = model.answers[question]
        is_correct = model.evaluate_answer(answer, correct_answer)

        # Обновляем статистику по источнику
        source_stats[source]['total'] += 1
        source_stats[source]['correct'] += int(is_correct)
        source_stats[source]['avg_confidence'] += confidence

        if confidence > 0.8:
            source_stats[source]['high_conf'] += 1
            total_stats['total_high_conf'] += 1
        elif confidence > 0.5:
            source_stats[source]['med_conf'] += 1
            total_stats['total_med_conf'] += 1
        else:
            source_stats[source]['low_conf'] += 1
            total_stats['total_low_conf'] += 1

        # Обновляем общую статистику
        total_stats['total_questions'] += 1
        total_stats['total_correct'] += int(is_correct)
        total_stats['avg_confidence'] += confidence

    # Вычисляем средние значения
    for source_stat in source_stats.values():
        if source_stat['total'] > 0:
            source_stat['avg_confidence'] /= source_stat['total']

    if total_stats['total_questions'] > 0:
        total_stats['avg_confidence'] /= total_stats['total_questions']

    return {'source_stats': source_stats, 'total_stats': total_stats}


def print_test_results(stats: Dict):
    """Вывод результатов тестирования в табличном виде"""
    if not stats:
        print("Нет данных для отображения")
        return

    # Таблица статистики по источникам
    source_table = []
    headers = ['Источник', 'Всего', 'Правильно', 'Точность', 'Выс.увер.', 'Ср.увер.', 'Низ.увер.', 'Ср.увер.']

    for source, stat in stats['source_stats'].items():
        if source != "Неизвестный источник" and stat['total'] > 0:
            accuracy = (stat['correct'] / stat['total']) * 100
            source_table.append([
                source,
                stat['total'],
                stat['correct'],
                f"{accuracy:.1f}%",
                stat['high_conf'],
                stat['med_conf'],
                stat['low_conf'],
                f"{stat['avg_confidence']:.2%}"
            ])

    # Общая статистика
    total = stats['total_stats']
    total_accuracy = (total['total_correct'] / total['total_questions']) * 100 if total['total_questions'] > 0 else 0

    print("\n=== Результаты тестирования модели ===")
    print(tabulate(source_table, headers=headers, tablefmt='grid'))

    print("\n=== Общая статистика ===")
    total_table = [
        ['Всего вопросов', total['total_questions']],
        ['Правильных ответов', total['total_correct']],
        ['Общая точность', f"{total_accuracy:.1f}%"],
        ['Высокая уверенность (>80%)', total['total_high_conf']],
        ['Средняя уверенность (50-80%)', total['total_med_conf']],
        ['Низкая уверенность (<50%)', total['total_low_conf']],
        ['Средняя уверенность', f"{total['avg_confidence']:.2%}"]
    ]
    print(tabulate(total_table, tablefmt='grid'))


if __name__ == "__main__":
    logger.info("Запуск программы")
    print("Запуск программы...")

    # Путь к данным - проверьте, что этот путь существует
    base_path = 'gost/back/py'

    # Проверка существования директории
    if not os.path.exists(base_path):
        print(f"Ошибка: директория {base_path} не найдена")
        print("Пожалуйста, укажите правильный путь к данным")
        sys.exit(1)

    # Проверка наличия поддиректорий
    if not (os.path.exists(os.path.join(base_path, "datasource/tables")) and
            os.path.exists(os.path.join(base_path, "datasource/infoblocks"))):
        print(f"Ошибка: в директории {base_path} не найдены папки 'tables' и/или 'infoblocks'")
        print("Структура директории должна быть следующей:")
        print(f"{base_path}/")
        print("    ├── tables/")
        print("    │   ├── 89-table1.json")
        print("    │   ├── 89-table2.json")
        print("    │   └── ...")
        print("    └── infoblocks/")
        print("        ├── 89-1.json")
        print("        ├── 89-2.json")
        print("        └── ...")
        sys.exit(1)

    # Создаем и инициализируем модель
    model = MaterialsQAModel()
    model.load_all_data(base_path)

    if not model.is_trained:
        logger.error("Модель не обучена")
        print("Ошибка: модель не обучена")
        sys.exit(1)

    # Проводим тестирование и выводим статистику
    print("\nПроведение тестирования модели...")
    test_stats = test_model_with_stats(model)
    print_test_results(test_stats)

    # Переходим к интерактивному режиму
    print("\nПереход к интерактивному режиму...")
    while True:
        print("\n" + "=" * 50)
        user_question = input("\nВведите ваш вопрос (или 'q' для выхода): ").strip()

        if user_question.lower() == 'q':
            break

        # Получаем ответ и статистику
        answer, confidence, source = model.generate_answer(user_question)

        # Находим похожие вопросы для анализа
        similar_questions = model.find_similar_questions(user_question, top_k=3)

        print("\n=== Результат анализа ===")
        print(f"\nВопрос: {user_question}")
        print(f"Ответ: {answer}")
        print(f"\nСтатистика:")
        print(f"- Источник: {source}")
        print(f"- Уверенность модели: {confidence:.2%}")

        # Анализ качества вопроса
        question_quality = "Высокое" if confidence > 0.8 else "Среднее" if confidence > 0.5 else "Низкое"
        print(f"- Качество соответствия вопроса: {question_quality}")

        # Вывод похожих вопросов
        if similar_questions:
            print("\nПохожие вопросы из базы:")
            for i, sq in enumerate(similar_questions, 1):
                print(f"{i}. Вопрос: {sq['question']}")
                print(f"   Схожесть: {sq['similarity']:.2%}")

        # Рекомендации по улучшению вопроса
        if confidence < 0.5:
            print("\nРекомендации по улучшению вопроса:")
            print("- Попробуйте переформулировать вопрос более конкретно")
            print("- Используйте ключевые термины из предметной области")
            if similar_questions:
                print("- Обратите внимание на формулировку похожих вопросов выше")

    logger.info("Программа завершена")
    print("\nПрограмма завершена")
