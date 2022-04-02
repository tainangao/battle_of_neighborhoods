from __future__ import print_function
import datetime
from airflow import models
from airflow.operators import bash_operator
from airflow.operators import python_operator
import configparser
import logging
from utils import clean_sales_data, assign_ntaname, clustering

logger = logging.getLogger("root")
logger.setLevel(logging.DEBUG)
# create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

config = configparser.ConfigParser()
config.read('config.ini')

default_dag_args = {
    # The start_date describes when a DAG is valid / can be run. Set this to a
    # fixed point in time rather than dynamically, since it is evaluated every
    # time a DAG is parsed. See:
    # https://airflow.apache.org/faq.html#what-s-the-deal-with-start-date
    'start_date': datetime.datetime(2022, 4, 2),
}

# Define a DAG (directed acyclic graph) of tasks.
# Any task you create within the context manager is automatically added to the
# DAG object.
with models.DAG(
        'the_battle_of_neighborhoods',
        schedule_interval=None,
        default_args=default_dag_args) as dag:
    # def greeting():
    #     import logging
    #     logging.info('Hello World!')
    #
    # # An instance of an operator is called a task. In this case, the
    # # hello_python task calls the "greeting" Python function.
    # hello_python = python_operator.PythonOperator(
    #     task_id='hello',
    #     python_callable=greeting)
    #
    # # Likewise, the goodbye_bash task calls a Bash script.
    # goodbye_bash = bash_operator.BashOperator(
    #     task_id='bye',
    #     bash_command='echo Goodbye.')
    #
    # # Define the order in which the tasks complete by using the >> and <<
    # # operators. In this example, hello_python executes before goodbye_bash.
    # hello_python >> goodbye_bash

    a = python_operator.PythonOperator(
        task_id='clean sales data',
        python_callable=clean_sales_data
    )

    b1 = python_operator.PythonOperator(
        task_id='enrich sales data',
        python_callable=assign_ntaname
    )

    b2 = python_operator.PythonOperator(
        task_id='clustering',
        python_callable=clustering
    )

    a >> [b1, b2]
