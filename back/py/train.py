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

        self.model_path = 'trained_model.pkl' # all infoblocks + tables
        #self.model_path = 'trained_model_promt_template.pkl' # promp template "Какие границы для испытания на временное сопротивление для широкополосного проката, марка стали Ст3сп, толщина проката 20, категория 5 для ГОСТ 14637-89?"

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


def test_model():
    logger.info("Начало тестирования модели")
    print("Начало тестирования модели...")

    model = MaterialsQAModel()
    base_path = 'gost/back/py'
    model.load_all_data(base_path)

    if not model.is_trained:
        logger.error("Модель не обучена")
        print("Ошибка: модель не обучена")
        return

    test_questions = model.questions
    source_stats = {}
    correct_answers = 0
    total_questions = 0

    print(f"\nНачало тестирования...\n")

    for i, question in enumerate(test_questions, 1):
        generated_answer, confidence, source = model.generate_answer(question)

        # Пропускаем вопросы с неизвестным источником
        if source == "Неизвестный источник":
            continue

        total_questions += 1
        print(f"\nВопрос {total_questions}: {question}")

        correct_answer = model.answers[question]

        if source not in source_stats:
            source_stats[source] = {'total': 0, 'correct': 0}
        source_stats[source]['total'] += 1

        is_correct = model.evaluate_answer(generated_answer, correct_answer)
        if is_correct:
            correct_answers += 1
            source_stats[source]['correct'] += 1

        print(f"Источник: {source}")
        print(f"Сгенерированный ответ: {generated_answer}")
        print(f"Правильный ответ: {correct_answer}")
        print(f"Уверенность: {confidence:.2f}")
        print("✓ Правильно" if is_correct else "✗ Неправильно")

    # Вывод статистики
    if total_questions > 0:
        print("\n=== Общая статистика ===")
        accuracy = (correct_answers / total_questions) * 100
        print(f"Всего вопросов: {total_questions}")
        print(f"Правильных ответов: {correct_answers}")
        print(f"Общая точность: {accuracy:.2f}%")

        print("\n=== Статистика по источникам ===")
        for source, stats in source_stats.items():
            source_accuracy = (stats['correct'] / stats['total']) * 100
            print(f"\n{source}:")
            print(f"Всего вопросов: {stats['total']}")
            print(f"Правильных ответов: {stats['correct']}")
            print(f"Точность: {source_accuracy:.2f}%")
    else:
        print("\nНет данных для анализа: все источники неизвестны")

    logger.info("Тестирование завершено")


if __name__ == "__main__":
    logger.info("Запуск программы")
    print("Запуск программы...")
    test_model()
    logger.info("Программа завершена")
    print("Программа завершена")