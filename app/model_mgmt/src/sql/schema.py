def query_text(project_id, dataset_id, table_id) -> str:
    sql_text = f"""
    SELECT
        column_name AS name,
        is_nullable,
        data_type
    FROM
        `{project_id}.{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
    WHERE
        table_name = '{table_id}'
    """
    return sql_text
