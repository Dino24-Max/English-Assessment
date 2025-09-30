"""
Question Bank Loader - Manages loading and filtering questions from question bank
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import random


class QuestionBankLoader:
    """Loads and manages questions from the question bank JSON file"""

    def __init__(self, question_bank_path: str):
        """
        Initialize the question bank loader

        Args:
            question_bank_path: Path to question_bank_sample.json file
        """
        self.question_bank_path = Path(question_bank_path)
        self.question_bank = None
        self.questions_by_operation = {}
        self.load_question_bank()

    def load_question_bank(self):
        """Load the question bank from JSON file"""
        if not self.question_bank_path.exists():
            raise FileNotFoundError(f"Question bank not found at {self.question_bank_path}")

        with open(self.question_bank_path, 'r', encoding='utf-8') as f:
            self.question_bank = json.load(f)

        # Organize questions by operation
        self._organize_by_operation()

    def _organize_by_operation(self):
        """Organize questions by operation type"""
        self.questions_by_operation = {
            'HOTEL': [],
            'MARINE': [],
            'CASINO': []
        }

        for question in self.question_bank['questions']:
            operation = question.get('operation', '').upper()
            if operation in self.questions_by_operation:
                self.questions_by_operation[operation].append(question)

    def get_questions_by_operation(self, operation: str, count: int = 21) -> List[Dict[str, Any]]:
        """
        Get filtered questions for a specific operation

        Args:
            operation: Operation type (HOTEL, MARINE, or CASINO)
            count: Number of questions to return (default 21)

        Returns:
            List of question dictionaries
        """
        operation = operation.upper()

        if operation not in self.questions_by_operation:
            raise ValueError(f"Invalid operation: {operation}. Must be HOTEL, MARINE, or CASINO")

        available_questions = self.questions_by_operation[operation]

        if len(available_questions) < count:
            raise ValueError(
                f"Not enough questions for {operation}. "
                f"Requested: {count}, Available: {len(available_questions)}"
            )

        # Get balanced selection across modules
        selected_questions = self._select_balanced_questions(available_questions, count)

        return selected_questions

    def _select_balanced_questions(self, questions: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Select questions with balanced distribution across modules

        Args:
            questions: Available questions
            count: Number of questions to select

        Returns:
            Balanced selection of questions
        """
        # Group questions by module
        by_module = {}
        for q in questions:
            module = q.get('module', 'Unknown')
            if module not in by_module:
                by_module[module] = []
            by_module[module].append(q)

        # Target distribution for 21 questions
        module_targets = {
            'Listening': 3,
            'TimeNumbers': 3,
            'Grammar': 4,
            'Vocabulary': 4,
            'Reading': 4,
            'Speaking': 3
        }

        selected = []

        # Select questions for each module
        for module, target in module_targets.items():
            module_questions = by_module.get(module, [])

            if len(module_questions) >= target:
                # Randomly select from available questions
                selected.extend(random.sample(module_questions, target))
            else:
                # Take all available if not enough
                selected.extend(module_questions)

        # If we don't have enough questions, fill with random remaining
        if len(selected) < count:
            remaining = [q for q in questions if q not in selected]
            needed = count - len(selected)
            if len(remaining) >= needed:
                selected.extend(random.sample(remaining, needed))
            else:
                selected.extend(remaining)

        # Sort by module order for consistent experience
        module_order = ['Listening', 'TimeNumbers', 'Grammar', 'Vocabulary', 'Reading', 'Speaking']
        selected.sort(key=lambda q: module_order.index(q.get('module', 'Unknown'))
                     if q.get('module') in module_order else 999)

        return selected[:count]

    def get_all_questions(self) -> List[Dict[str, Any]]:
        """Get all questions from the question bank"""
        return self.question_bank['questions']

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the question bank"""
        return self.question_bank.get('statistics', {})

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about the question bank"""
        return self.question_bank.get('metadata', {})

    def get_question_count_by_operation(self, operation: str) -> int:
        """
        Get the number of available questions for an operation

        Args:
            operation: Operation type (HOTEL, MARINE, or CASINO)

        Returns:
            Number of questions available
        """
        operation = operation.upper()
        return len(self.questions_by_operation.get(operation, []))
