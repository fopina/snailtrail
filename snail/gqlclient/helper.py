class GQL:
    _TYPE = 'query'

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

    def execute(self, client, **kwargs):
        return client.query(
            self.operation_name,
            self._variable_values(),
            f'''
            {self._TYPE} {self.operation_name}({self._variable_types()}) {{
                {self.name}({self._variable_names()}) {{
                {self.query}
                }}
            }}
            ''',
            **kwargs,
        )

    def __add__(self, value):
        if isinstance(value, GQL):
            return GQLUnion(self, value)
        elif isinstance(value, GQLUnion):
            value.gqls.insert(0, self)
            return value
        raise ValueError('Can only concatenate with GQL instances')


class GQLMutation(GQL):
    _TYPE = 'mutation'


class GQLUnion:
    def __init__(self, *gqls, prefix='q'):
        self.gqls: list[GQL] = gqls[:] if gqls else []
        self._prefix = prefix

    @property
    def operation_name(self):
        if self.gqls:
            return self.gqls[0].operation_name
        return 'query'

    def _variable_types(self):
        return ', '.join(f'${k}{i}: {v[0]}' for i, gql in enumerate(self.gqls) for k, v in gql.variables.items())

    def _variable_values(self):
        return {f'{k}{i}': v[1] for i, gql in enumerate(self.gqls) for k, v in gql.variables.items()}

    def _variable_names_renamed(self, index):
        gql = self.gqls[index]
        return ', '.join(f'{k}: ${k}{index}' for k in gql.variables)

    def execute(self, client):
        if not self.gqls:
            return
        if len(self.gqls) == 1:
            r = self.gqls[0].execute(client)
            # also support "indexed"
            r[f'{self._prefix}0'] = r[self.gqls[0].name]
            return r

        body = [
            f'''
            {self._prefix}{i}: {gql.name}({self._variable_names_renamed(i)}) {{
            {gql.query}
            }}
            '''
            for i, gql in enumerate(self.gqls)
        ]
        return client.query(
            self.operation_name,
            self._variable_values(),
            f'''
            query {self.operation_name}({self._variable_types()}) {{
            {''.join(body)}
            }}
            ''',
        )

    def __add__(self, value):
        if isinstance(value, GQL):
            self.gqls.append(value)
        elif isinstance(value, GQLUnion):
            self.gqls.extend(value.gqls)
        else:
            raise ValueError('Can only concatenate with GQL instances')
        return self
