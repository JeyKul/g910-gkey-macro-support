from copy import deepcopy

from g910_gkeys.misc.config import Config as BaseConfig


class LayerState:
    def __init__(self):
        self.bank = 'MEMORY_1'
        self.shifted = False

    def select(self, event):
        if event == 'MEMORY_RECORD':
            self.shifted = not self.shifted
        elif event in ('MEMORY_1', 'MEMORY_2', 'MEMORY_3'):
            self.bank = event
            self.shifted = False
        else:
            raise ValueError('Unknown profile event: ' + str(event))
        return self.bank + ('_MR' if self.shifted else '')


class Config(BaseConfig):
    def validate_config(self, config_dic):
        result = super().validate_config(config_dic)
        source_profiles = config_dic.get('profiles', {})
        for bank in ('MEMORY_1', 'MEMORY_2', 'MEMORY_3'):
            name = bank + '_MR'
            layer = deepcopy(result['profiles']['MEMORY_RECORD'])
            if name in source_profiles:
                for i in range(1, 10):
                    key = 'MACRO_' + str(i)
                    if key in source_profiles[name]:
                        layer[key] = self.get_key_action(config_dic, name.removeprefix('MEMORY_'), i)
            result['profiles'][name] = layer
        return result

    def update_config(self):
        self.config = None
        self.read()
