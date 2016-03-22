# A parser to parse the topics and questions schema for a single Analysis Type
# and populate the database

import json

from thresher.models import *
from collections import namedtuple

###### EXCEPTIONS ######

########################

class TopicsSchemaParser(object):
    """
    Parses a json schema of topics and questions and populates the database
    """
    def __init__(self, topic_obj, schema, dependencies):
        """
        schema: a json schema as a string or loaded json with subtopics
        dependencies: the list of answers that point to another question
        topic_obj: the Topic object that is the parent of subtopics in schema
        """
        self.topic_obj = topic_obj
        # if the schema is a string, tries to load it as json, otherwise,
        # assumes it's already json
        self.schema_json = json.loads(schema) if (isinstance(schema, str) or isinstance(schema, unicode)) else schema
        # ensure that the analysis_type is valid
        if not isinstance(topic_obj, Topic):
            raise ValueError("schema must be an instance of Topic\
                    model")
        self.dep = dependencies
        self.clean_dependencies()

    def clean_dependencies(self):
        """
        Returns a list of named tuples that represent each dependency:
        [Dependency(topic, question, answer, next_topic, next_topic)]
        Also converts strings to integers.
        """
        Dependency = namedtuple('Dependency', ['topic', 'question', 'answer', 'next_topic', 'next_question'])
        clean_dep = []
        for dep in self.dep:
            answer, next_question = dep
            new_dep = answer.split(".")
            new_dep.extend(next_question.split("."))
            new_dep = [int(val) if val != 'any' else val for val in new_dep]
            clean_dep.append(Dependency(*new_dep))
        self.dep = clean_dep

    def load_answers(self, answers, question):
        """
        Creates the answers instances for a given question
        """
        # find the corresponding topic and question ids
        for answer_args in answers:
            # rename the id to answer_id
            answer_args['answer_id'] = answer_args.pop('id')
            # rename text to answer_content
            answer_args['answer_content'] = answer_args.pop('text')
            # create the next question reference, it will be rewritten in
            # load_next_question
            answer_args['question'] = question
            # Create the answer in the database
            answer = Answer.objects.create(**answer_args)

    def load_questions(self, questions, topic):
        """
        Creates the questions instances for the given topic
        """
        for question_args in questions:
            # Rename the id to question_id
            question_args['question_id'] = question_args.pop('id')
            # Rename text to question_text
            question_args['question_text'] = question_args.pop('text')
            # Create the topic
            question_args['topic'] = topic
            # Store the answers for later
            answers = question_args.pop('answers')
            # Create the Question
            question = Question.objects.create(**question_args)
            # Load the question's answers
            self.load_answers(answers, question)

    def load_topics(self):
        """
        loads all the topics, their questions and their answers
        """
        for topic_args in self.schema_json:
            # get the questions to add them later
            questions = topic_args.pop('questions')
            # replace id with order
            topic_args['order'] = topic_args.pop('id')
            # set the analysis type - not necessary, getting refactored into Topic
            # topic_args['analysis_type'] = self.analysis_type
            # set reference to parent
            topic_args['parent'] = self.topic_obj
            # Create the topic with the values in topic_args
            topic = Topic.objects.create(**topic_args)
            self.load_questions(questions, topic)
        self.load_next_question()
        self.load_dependencies()

    def load_next_question(self):
        """
        Loads all mandatory next_questions to Answer objects. 
        If an answer does not point to another question, that 
        signals the end.
        """
        topics = Topic.objects.filter(parent=self.topic_obj)
        for topic in topics:
            stop_question_id = 0
            for dep in self.dep:
                if dep.topic == topic.topic_id:
                    stop_question_id = dep.next_question
                    break
            if stop_question_id:
                for question_id in range(1, stop_question_id):
                    question = Question.objects.filter(topic=topic, 
                                                       question_id=question_id)
                    next_question = Question.objects.filter(
                        topic=topic, question_id=question_id + 1)
                    answers = Answer.objects.filter(question=question)
                    for answer in answers:
                        answer.next_question = next_question


    def load_dependencies(self):
        topics = Topic.objects.filter(parent=self.topic_obj)
        for dep in self.dep:
            topic = topics.filter(order=dep.topic)
            question = Question.objects.filter(topic=topic, 
                                               question_id=dep.question)
            next_question = Question.objects.filter(
                topic=topic, question_id=dep.next_question)[0]
            if dep.answer == 'any':
                answers = Answer.objects.filter(question=question)
            else:
                answers = Answer.objects.filter(question=question,
                                                answer_id=dep.answer)
            for answer in answers:
                answer.next_question = next_question
                answer.save()

