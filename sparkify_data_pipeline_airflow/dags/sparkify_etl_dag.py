from datetime import datetime, timedelta
import os
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators import (StageToRedshiftOperator, LoadFactOperator,
                                LoadDimensionOperator, DataQualityOperator)
from helpers import SqlQueries

# AWS_KEY = os.environ.get('AWS_KEY')
# AWS_SECRET = os.environ.get('AWS_SECRET')

default_args = {
    'owner': 'kene',
    'depends_on_past': False,
    'start_date': datetime(2020, 3, 7),
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
    'email_on_retry': False
}

dag = DAG('sparkify_etl_dag',
          default_args=default_args,
          description='Load and transform data in Redshift with Airflow',
        #   schedule_interval='0 * * * *'
        )

start_operator = DummyOperator(task_id='Begin_execution',  dag=dag)

stage_events_to_redshift = StageToRedshiftOperator(
    task_id='Stage_events',
    dag=dag,
    table='staging_events',
    redshift_conn_id='redshift',
    aws_credentials_id='aws_credentials',
    s3_bucket='udacity-dend',
    s3_key='log_data',
    json_paths='log_json_path.json',
    # use_partitioned=True,
    # partition_template='{execution_date.year}/{execution_date.month}'
)

stage_songs_to_redshift = StageToRedshiftOperator(
    task_id='Stage_songs',
    dag=dag,
    table='staging_songs',
    redshift_conn_id='redshift',
    aws_credentials_id='aws_credentials',
    s3_bucket='udacity-dend',
    s3_key='song_data',
)

load_songplays_table = LoadFactOperator(
    task_id='Load_songplays_fact_table',
    dag=dag,
    redshift_conn_id='redshift',
    query=SqlQueries.songplay_table_insert,
    target_table='songplays'
)

load_user_dimension_table = LoadDimensionOperator(
    task_id='Load_user_dim_table',
    dag=dag,
    redshift_conn_id='redshift',
    query=SqlQueries.user_table_insert,
    target_table='users'
)

load_song_dimension_table = LoadDimensionOperator(
    task_id='Load_song_dim_table',
    dag=dag,
    redshift_conn_id='redshift',
    query=SqlQueries.song_table_insert,
    target_table='songs'
)

load_artist_dimension_table = LoadDimensionOperator(
    task_id='Load_artist_dim_table',
    dag=dag,
    redshift_conn_id='redshift',
    query=SqlQueries.artist_table_insert,
    target_table='artists'
)

load_time_dimension_table = LoadDimensionOperator(
    task_id='Load_time_dim_table',
    dag=dag,
    redshift_conn_id='redshift',
    query=SqlQueries.time_table_insert,
    target_table='time'
)

quality_check_staging_events_table = DataQualityOperator(
    task_id='quality_check_staging_events_table',
    dag=dag,
    redshift_conn_id='redshift',
    table='staging_events'
)

quality_check_staging_songs_table = DataQualityOperator(
    task_id='quality_check_staging_songs_table',
    dag=dag,
    redshift_conn_id='redshift',
    table='staging_songs'
)

quality_check_songplays_table = DataQualityOperator(
    task_id='quality_check_songplays_table',
    dag=dag,
    redshift_conn_id='redshift',
    table='songplays',
    dq_checks=[{'check_sql': "SELECT COUNT(*) FROM songplays WHERE playid is null", 'expected_result': 0}]
)

quality_check_users_table = DataQualityOperator(
    task_id='quality_check_users_table',
    dag=dag,
    redshift_conn_id='redshift',
    table='users',
    dq_checks=[{'check_sql': "SELECT COUNT(*) FROM users WHERE userid is null", 'expected_result': 0}]
)

quality_check_artists_table = DataQualityOperator(
    task_id='quality_check_artists_table',
    dag=dag,
    redshift_conn_id='redshift',
    table='artists',
    dq_checks=[{'check_sql': "SELECT COUNT(*) FROM artists WHERE artistid is null", 'expected_result': 0}]
)

quality_check_songs_table = DataQualityOperator(
    task_id='quality_check_songs_table',
    dag=dag,
    redshift_conn_id='redshift',
    table='songs',
    dq_checks=[{'check_sql': "SELECT COUNT(*) FROM songs WHERE songid is null", 'expected_result': 0}]
)

quality_check_time_table = DataQualityOperator(
    task_id='quality_check_time_table',
    dag=dag,
    redshift_conn_id='redshift',
    table='time',
    dq_checks=[{'check_sql': "SELECT COUNT(*) FROM time WHERE start_time is null", 'expected_result': 0}]
)

end_operator = DummyOperator(task_id='Stop_execution',  dag=dag)

start_operator >> [stage_events_to_redshift, stage_songs_to_redshift]
stage_events_to_redshift >> quality_check_staging_events_table
stage_songs_to_redshift >> quality_check_staging_songs_table
[quality_check_staging_events_table, quality_check_staging_songs_table] >> load_songplays_table >> quality_check_songplays_table
quality_check_songplays_table >> load_time_dimension_table >> quality_check_time_table
quality_check_staging_events_table >> load_user_dimension_table >> quality_check_users_table
quality_check_staging_songs_table >> [load_artist_dimension_table, load_song_dimension_table]
load_artist_dimension_table >> quality_check_artists_table
load_song_dimension_table >> quality_check_songs_table
[quality_check_time_table, quality_check_users_table, quality_check_songs_table, quality_check_artists_table] >> end_operator
