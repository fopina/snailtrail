class GQL:
    def __init__(self, name, query, variables, operation_name=None):
        self.name = name
        self.variables = variables
        self.query = query
        self.operation_name = operation_name or 'query'

    def _variable_names(self):
        return ', '.join(f'{k}: ${k}' for k in self.variables)

    def _variable_types(self):
        return ', '.join(f'${k}: {v[0]}' for k, v in self.variables.items())

    def _variable_values(self):
        return {k: v[1] for k, v in self.variables.items()}

    def execute(self, client):
        return client.query(
            self.operation_name,
            self._variable_values(),
            f'''
            query {self.operation_name}({self._variable_types()}) {{
                {self.name}({self._variable_names()}) {{
                {self.query}
                }}
            }}
            ''',
        )
