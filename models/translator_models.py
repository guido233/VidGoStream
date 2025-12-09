from texttranslator.translator import TextTranslator as ZhipuTranslatorImpl
from .base import BaseTranslator

class ZhipuTranslator(BaseTranslator):
    """智谱AI翻译模型"""
    
    def __init__(self, api_key, model='glm-4', base_url='https://open.bigmodel.cn/api/paas/v4/'):
        """
        初始化智谱AI翻译模型
        
        Args:
            api_key: 智谱API密钥
            model: 使用的模型名称
            base_url: API基础URL
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._translator = ZhipuTranslatorImpl(api_key, model=model, base_url=base_url)
    
    def translate_file(self, input_file, output_file, target_lang='zh'):
        """
        翻译文件
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            target_lang: 目标语言
            
        Returns:
            bool: 是否成功
        """
        return self._translator.translate_file(input_file, output_file, target_lang)

