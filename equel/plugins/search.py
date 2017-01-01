# Search Plugins
from .generic import BasePlugin, GenericPlugin, BaseShortcutPlugin, EQUELPluginException

class BaseSearchPlugin(GenericPlugin):
    """Search specific plugin attributes"""
    # Allow return value of plugin to be used as search filter, e.g. in further search subexpressions
    filterable = False

class GenericSearchPlugin(BaseSearchPlugin):
    """Convert EQUEL into JSON and wrap into query attribute"""
    name = "Generic Search Plugin"
    description = "Generic EQUEL to JSON conversion with wrapping into query attribute"
    # TODO: this currently overwrites everything in generated ES DSL JSON
    #filterable = True

    def apply(self, verb, params, parser, ctx):
        return { "query": super().apply(verb, params, parser, ctx) }

class ESQueryStringPlugin(BaseSearchPlugin):
    """Convert Elasticsearch query string into Query DSL structure"""
    name = "Elasticsearch Query String Plugin"
    description = "Convert Elasticsearch query string into Query DSL structure"

    def apply(self, verb, query, parser, ctx):
        return { "query": { "query_string": { "query": query } } }

class SearchShortcutPlugin(BaseShortcutPlugin):
    """
    Converts given value into a query_string query. Prefixes:
    ':': Use ES default as default operator (currently OR)
    '&': AND as default operator
    """
    name = "Search shortcut plugin"
    description = "Convert value into query_string query"
    filterable = True

    def apply(self, prefix, value, parser, ctx):
        res = { "query_string": { "query": value } }
        if prefix == "&":
            res["query_string"]["default_operator"] = "AND"
        return { "query": res }

class SortPlugin(BaseSearchPlugin):
    """
    Sort entries by addition of a 'sort' query option. Parameter s contains one or multiple field names.
    If suffixed with + or - the sort order is added explicitely (asc/desc).
    """
    name = "Search result sort plugin"
    description = "Sort search results"

    def __init__(self):
        super().__init__()
        self.sortfields = list()

    def appendField(self, field):
        if field.endswith("+"):
            self.sortfields.append({ field[:-1] : { "order": "asc" } })
        if field.endswith("-"):
            self.sortfields.append({ field[:-1] : { "order": "desc" } })
        else:
            self.sortfields.append(field)

    def apply(self, verb, params, parser, ctx):
        try:
            fields = params["unnamed_list"]
        except KeyError:
            raise EQUELPluginException("Expression 'sort' requires list of fields")

        if len(fields) == 0:
            raise EQUELPluginException("List of fields of sort expression must not be empty")
        elif type(fields[0]) == list:
            raise EQUELPluginException("Only one list of fields in sort expression is allowed")

        for field in fields:
            self.appendField(field)

        return { "sort": self.sortfields }

class FieldFilterPlugin(BaseSearchPlugin):
    """
    Filter fields from search result. Parameters:
    [field,...]: include these fields
    exclude=[field,...]: exclude these fields
    """
    name = "Filter fields from search result plugin"
    description = "Filters fields from search result documents"

    def apply(self, verb, params, parser, ctx):
        try:
            include = params["unnamed_list"]
        except KeyError:
            include = None

        try:
            exclude = params["exclude"]
        except KeyError:
            exclude = None

        if include and len(include) > 0 and type(include[0]) == list or exclude and len(exclude) > 0 and type(exclude[0]) == list:
            raise EQUELPluginException("Only one list of fields in fields expression is allowed")

        if not include and not exclude:
            return {}

        filters = dict()
        if include:
            filters["include"] = include
        if exclude:
            filters["exclude"] = exclude
        return { "_source": filters }

class NestQueryPlugin(BaseSearchPlugin):
    """Wrap current query into nested query"""
    name = "Nest current query"
    description = "Wraps current query into nested query"
    # TODO: make it filterable - last created ES DSL expression has to be stored somewhere

    def apply(self, verb, params, parser, ctx):
        if 'path' not in params:
            raise EQUELPluginException("Search subquery 'nest' requires path parameter")
        query = parser.query['query']
        query = { 'nested': { 'path': params['path'], 'query': query } }
        parser.query['query'] = query
        return {}

class ScriptQueryPlugin(BaseSearchPlugin):
    """Perform a script query"""
    name = "Script query"
    description = "Perform a script query (default: painless)"
    filterable = True

    def apply(self, verb, params, parser, ctx):
        if 'unnamed' not in params:
            raise EQUELPluginException("Search subquery 'script' requires a script as unnamed parameter")
        script = params['unnamed']

        try:
            lang = params['lang']
        except KeyError:
            lang = "painless"

        return { "script": { "script": { "lang": lang, "inline": script } } }