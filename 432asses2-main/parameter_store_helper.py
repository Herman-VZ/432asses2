import boto3
import os
import logging

logger = logging.getLogger(__name__)  # FIXED

class ParameterStoreHelper:
    def __init__(self):  # FIXED: __init__ not init
        self.ssm = boto3.client('ssm', region_name='ap-southeast-2')
        self.cache = {}

    def get_param(self, name, default=None):
        if name in self.cache:
            return self.cache[name]
        
        try:
            response = self.ssm.get_parameter(Name=name)
            value = response['Parameter']['Value']
            self.cache[name] = value
            logger.info(f"✅ Loaded parameter: {name}")
            return value
        except:
            logger.warning(f"⚠️ Using default for: {name}")
            return default

param_helper = ParameterStoreHelper()