import quantipy.core.helpers.functions as helpers
from operator import add, sub, mul, div
import pandas as pd
import copy


class View(object):
    def __init__(self, link, name, kwargs=None):
        #self._view_attributes = ['meta', 'link', 'dataframe', 'rbases', 'cbases', '_kwargs']
        self._kwargs = kwargs.copy()
        self.name = name
        self._link_meta(link)
        self.dataframe = pd.DataFrame()
        self._notation = None
        self.rbases = None
        self.cbases = None
        self.grp_text_map = None

    def meta(self):
        """
        Get a summary on a View's meta information.

        Returns
        -------
        viewmeta: dict
            A dictionary that contains global aggregation information.
        """
        viewmeta = {
                    'agg':
                    {
                     'is_weighted': self.is_weighted(),
                     'weights': self.get_std_params()[3],
                     'method': self._method(),
                     'name': self._shortname(),
                     'fullname': self._notation,
                     'text': self.get_std_params()[4],
                     'grp_text_map': self.grp_text_map,
                     'is_block': self._is_block()
                     },
                    'x': self._x,
                    'y': self._y,
                    'shape': self.dataframe.shape
                    }
        return viewmeta

    def _link_meta(self, link):
        metas = []
        xname = link.x
        yname = link.y
        filemeta = link.get_meta()
        if filemeta['columns'] is None:
            metas = [{'name': xname, 'is_multi': False, 'is_nested': False},
                     {'name': yname, 'is_multi': False, 'is_nested': False}]
        else:
            mc = ['dichotomous set', 'categorical set', 'delimited set']
            for name in [xname, yname]:
                if name in filemeta['columns']:
                    dtype = filemeta['columns'][name]['type']
                elif name in filemeta['masks']:
                    dtype = filemeta['masks'][name]['type']
                elif name == '@':
                    dtype = None
                is_multi = True if dtype in mc else False
                is_nested = True if '>' in name else False
                is_array = True if xname in filemeta['masks'].keys() else False
                metas.append(
                    {'name': name,
                     'is_multi': is_multi,
                     'is_nested': is_nested,
                     'is_array': is_array}
                    )
        self._x = metas[0]
        self._y = metas[1]

    def _grp_text_map(self, logic, calc):
        if logic is not None:
            calc_only = self._kwargs.get('calc_only', False)
            net_texts = []
            net_names = []
            for l in logic:
                net_text = l.get('text', None)
                if net_text is not None:
                    del l['text']
                    net_texts.append(net_text)
                else:
                    net_texts.append(None)
                net_names.extend([key for key in l.keys()
                                   if not key == 'expand'])
            grp_text_map = {name: text
                            for name, text in zip(net_names, net_texts)}
            if calc is not None:
                calc_text = calc.get('text', None)
                if calc_text is not None:
                    del calc['text']
                if not calc_only:
                    grp_text_map[calc.keys()[0]] = calc_text
                else:
                    grp_text_map = {calc.keys()[0]: calc_text}
        else:
            grp_text_map = None
        return grp_text_map


    def notation(self, method, condition):
        """
        Generate the View's Stack key notation string.

        Parameters
        ----------
        aggname, shortname, relation : str
            Strings for the aggregation name, the method's shortname and the
            relation component of the View notation.

        Returns
        -------
        notation: str
            The View notation.
        """
        notation_strct = 'x|{}|{}|{}|{}|{}'
        axis, _, rel_to, weights, _ = self.get_std_params()
        name = self.name
        if rel_to is None:
            rel_to = ''
        if weights is None:
            weights = ''
        if condition is None:
            condition = ':'
        elif condition in ['x:', ':']:
            condition = condition
        else:
            if not 't.' in method:
                if axis == 'x':
                    condition = condition + ':'
                else:
                    condition = ':' + condition
        return notation_strct.format(method, condition, rel_to, weights, name)

    def get_std_params(self):
        """
        Provides the View's standard kwargs with fallbacks to default values.

        Returns
        -------
        std_parameters : tuple
            A tuple of the common kwargs controlling the general View method
            behaviour: axis, relation, rel_to, weights, text
        """
        return (
            self._kwargs.get('axis', None),
            self._kwargs.get('condition', None),
            self._kwargs.get('rel_to', None),
            self._kwargs.get('weights', None),
            self._kwargs.get('text', '')
            )

    def get_edit_params(self):
        """
        Provides the View's Link edit kwargs with fallbacks to default values.

        Returns
        -------
        edit_params : tuple
            A tuple of kwargs controlling the following supported Link data
            edits: logic, calc, ...
        """
        logic = copy.deepcopy(self._kwargs.get('logic', None))
        calc = copy.deepcopy(self._kwargs.get('calc', None))
        if (not logic is None and (isinstance(logic, list) and not
                isinstance(logic[0], dict)) or isinstance(logic, (dict, tuple))):
            logic = [{self.name: logic}]
        self.grp_text_map = self._grp_text_map(logic, calc)
        return (
            logic,
            self._kwargs.get('expand', None),
            calc,
            self._kwargs.get('exclude', None),
            self._kwargs.get('rescale', None)
            )

    def fulltext_for_stat(self, stat):
        """
        Creates the full text (=label) meta for ``descriptives()`` view
        aggregations. The full text consists of the name of the figure and
        the passed suffix from view method's "text" kwarg.

        Parameters
        ----------
        stat : str
            Name of the stat. figure.

        Returns
        -------
        fulltext : str
            The text that is passed into the meta component of the View.
        """
        texts = {
            'mean': 'Mean',
            'sem': 'Std. err. of mean',
            'median': 'Median',
            'stddev': 'Std. dev.',
            'var': 'Sample variance',
            'varcoeff': 'Coefficient of variation',
            'min': 'Min',
            'max': 'Max'
        }
        text = self.get_std_params()[-1]
        if text == '':
            self._kwargs['text'] = texts[stat]
        else:
            self._kwargs['text'] = '%s %s' % (texts[stat], self._kwargs['text'])


    def _frequency_condition(self, logic, conditionals, expand):
        axis = self._kwargs.get('axis', 'x')
        if conditionals: conditionals = list(reversed(conditionals))
        logic_codes = []
        for grp in logic:
            if isinstance(grp.values()[0], (dict, tuple)):
                codes = conditionals.pop()
                logic_codes.append(codes)
            else:
                expand_cond = expand
                if 'expand' in grp.keys():
                    grp = copy.deepcopy(grp)
                    expand_cond = grp['expand']
                    del grp['expand']
                codes = '{'+','.join(map(str, grp.values()[0]))+'}'
                # codes = str(grp.values()[0])
                # codes = codes.replace(' ', '').replace('[', '{').replace(']', '}')
                if expand_cond is None:
                    logic_codes.append("{}[{}]".format(axis, codes))
                elif expand_cond == 'after':
                    logic_codes.append("{}[{}+]".format(axis, codes))
                else:
                    logic_codes.append("{}[+{}]".format(axis, codes))
        return logic_codes
        # return '-'.join([codes for codes in logic_codes])

    def _descriptives_condition(self, link):
        try:
            if link.x in link.get_meta()['masks'].keys():
                values = link.get_meta()['lib']['values'][link.x]
            else:
                values = link.get_meta()['columns'][link.x].get('values', None)
                if 'lib@values' in values:
                    vals = values.split('@')[-1]
                    values = link.get_meta()['lib']['values'][vals]
            x_values = [int(x['value']) for x in values]
            if self.missing():
                x_values = [x for x in x_values if not x in self.missing()]
            if self.rescaling():
                x_values = [x if not x in self.rescaling()
                            else self.rescaling()[x] for x in x_values]
            if self.missing() or self.rescaling():
                condition = 'x[{}]'.format('{'+','.join(map(str, x_values))+'}')
            else:
                condition = 'x' if self._kwargs.get('axis', 'x') == 'x' else 'y'
                # if self._kwargs.get('axis', 'x') == 'x':
                #     condition = 'x'
                # else:
                #     condition = 'y'
        except:
            condition = 'x' if self._kwargs.get('axis', 'x') == 'x' else 'y'
            # if self._kwargs.get('axis', 'x'):
            #     condition = 'x'
            # else:
            #     condition = 'y'
        return condition

    def _calc_condition(self, logic, conditions, calc):
        op = calc.values()[0][1]
        val1, val2 = calc.values()[0][0], calc.values()[0][2]
        symbol_map = {add: '+', sub: '-', mul: '*', div: '/'}
        calc_strct = '{}{}{}'
        if logic:
            cond_names = []
            for l in logic:
                cond_names.extend([key for key in l.keys()
                                   if not key == 'expand'])
            name_cond_pairs = zip(cond_names, conditions)
            cond_map = {name: cond for name, cond in name_cond_pairs}
            v1 = cond_map[val1] if val1 in cond_map.keys() else val2
            v2 = cond_map[val2] if val2 in cond_map.keys() else val2
        else:
            v1 = val1 if isinstance(val1, list) else conditions
            v2 = val2 if isinstance(val2, list) else conditions
        calc_string = calc_strct.format(v1, symbol_map[op], v2)
        calc_string = calc_string.replace('+{', '{').replace('}+', '}')
        calc_string = calc_string.replace('x', '')
        calc_string = calc_string.replace('[', '').replace(']', '')
        calc_string = 'x[{}]'.format(calc_string)
        return calc_string

    def spec_condition(self, link, conditionals=None, expand=None):
        """
        Updates the View notation's condition component based on agg. details.

        Parameters
        ----------
        link : Link

        Returns
        -------
        relation_string : str
            The relation part of the View name notation.
        """
        logic = self.get_edit_params()[0]
        stat = self._kwargs.get('stats', 'mean')
        calc = self.get_edit_params()[2]
        if logic is not None:
            condition = self._frequency_condition(logic, conditionals, expand)
        elif stat is not None:
            condition = self._descriptives_condition(link)
        else:
            condition = 'x' if self._kwargs.get('axis', 'x') == 'x' else 'y'
        if calc is not None:
                calc_cond = self._calc_condition(logic, condition, calc)
                if not self._kwargs.get('calc_only', False):
                    if logic:
                        condition = '{},{}'.format(','.join(condition), calc_cond)
                    else:
                        condition = '{},{}'.format(condition, calc_cond)
                else:
                    condition = calc_cond
        else:
            if logic: condition = ','.join(condition)
        return condition

        # else:
        #     condition = self._descriptives_condition(link)
        #     calc = self.get_edit_params()[2]
        #     if calc:
        #         calc_cond = self._calc_condition(None, condition, calc)
        #         if not self._kwargs.get('calc_only', False):
        #             condition = '{},{}'.format(condition, calc_cond)
        #         else:
        #             condition = calc_cond
        # return condition





    def missing(self):
        """
        Returns any excluded value codes.
        """
        return self._kwargs.get('exclude', None)

    def rescaling(self):
        """
        Returns the rescaling specification of value codes.
        """
        return self._kwargs.get('rescale', None)

    def weights(self):
        """
        Returns the weight variable name used in the aggregation.
        """
        return self._kwargs.get('weights', None)

    def is_weighted(self):
        """
        Tests if the View is performed on weighted data.
        """
        notation = self._notation.split('|')
        if len(notation[4]) > 0:
            return True
        else:
            return False

    def is_pct(self):
        """
        Tests if the View is a percentage representation of a frequency.
        """
        notation = self._notation.split('|')
        if notation[1] == 'f':
            if len(notation[3]) > 0:
                return True
            else:
                return False
        else:
            return False

    def is_base(self):
        """
        Tests if the View is a base size aggregation.
        """
        notation = self._notation.split('|')
        if notation[1] == 'f':
            if len(notation[2]) == 2:
                return True
            else:
                return False
        else:
            return False


    def is_net(self):
        """
        Tests if the View is a code group/net aggregation.
        """
        notation = self._notation.split('|')
        if notation[1] == 'f':
            if self._has_code_expr():
                return True
            else:
                return False
        else:
            return False

    def is_counts(self):
        """
        Tests if the View is a count representation of a frequency.
        """
        notation = self._notation.split('|')
        if notation[1] == 'f':
            if len(notation[3]) == 0:
                return True
            else:
                return False
        else:
            return False

    def is_stat(self):
        """
        Tests if the View is a sample statistic.
        """
        if self.meta()['agg']['method'] == 'descriptives':
            return True
        else:
            return False

    def _is_test(self):
        notation = self._notation.split('|')
        if 't.' in notation[1]:
            return True
        else:
            return False

    def is_meanstest(self):
        """
        Tests if the View is a statistical test of differences in means.
        """
        if self._is_test():
            teststr = self._notation.split('|')[1].split('.')
            if teststr[1] == 'means':
                return float(teststr[3])/100
            else:
                return False
        else:
            return False

    def is_propstest(self):
        """
        Tests if the View is a statistical test of differences in proportions.
        """
        if self._is_test():
            teststr = self._notation.split('|')[1].split('.')
            if teststr[1] == 'props':
                return float(teststr[3])/100
            else:
                return False
        else:
            return False

    def _is_block(self):
        notation = self._notation.split('|')
        if notation[1] in ['f', 'f.c:f']:
            conditions = notation[2].split('[')
            if conditions:
                if len(conditions) > 2:
                    return True
                else:
                    return False
            else:
                False
        else:
            False

    def _has_code_expr(self):
        notation = self._notation.split('|')
        if len(notation[2]) > 3:
            return True
        else:
            return False

    def _shortname(self):
        return self.name.split('|')[-1]

    def _method(self):
        method_part = self._notation.split('|')[1]
        if 'd.' in method_part:
            return 'descriptives'
        elif 'f.' in method_part or method_part == 'f':
            return 'frequency'
        elif 't.' in method_part:
            return 'coltests'
        else:
            return method_part


    def __repr__(self):
        """ Message to be printed in stdout (print self)

            Example: << View.View Rows: 4, Columns: 3, Has Meta:False >>
        """
        row_count = len(self.dataframe.index)
        columns_count = len(self.dataframe.columns)
        return '%s' % (self.dataframe)
