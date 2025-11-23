import os
import time
from typing import Optional
from pathlib import Path
import alibabacloud_oss_v2 as oss
from camera_surveillance.tools.workspace import log_with_timestamp


class OSSHandler:
    """OSS存储处理器"""
    
    def __init__(self, region: str= 'cn-hangzhou', endpoint: str = None):
        """
        初始化OSS处理器
        :param bucket_name: OSS桶名称
        :param endpoint: OSS端点
        :param access_key_id: 访问密钥ID
        :param access_key_secret: 访问密钥密钥
        """

        credentials_provider = oss.credentials.StaticCredentialsProvider(
            access_key_id="LTAI5tS12D3EPVxkNDUfaHMe",
            access_key_secret="UywTumzfqoJoXB2gm9WmDY27E1vces"
        )
        
        cfg = oss.config.load_default()
        cfg.credentials_provider = credentials_provider
        cfg.region = region

        if endpoint:
            cfg.region = endpoint

        self.client = oss.Client(cfg)

    def upload_file(self, bucket: str, object_key: str, file_path: str) -> bool:
        """
        上传单个文件到OSS

        Args:
            bucket: 存储空间名称
            object_key: 对象键（OSS中的文件路径）
            file_path: 本地文件路径

        Returns:
            上传是否成功
        """
        try:
            # 打开本地文件进行读取
            with open(file_path, 'rb') as f:
                data = f.read()

            # 上传文件
            result = self.client.put_object(oss.PutObjectRequest(
                bucket=bucket,
                key=object_key,
                body=data,
            ))

            # logging.warning(f"文件上传成功: {file_path} -> {object_key}, status code: {result.status_code}")
            return True

        except Exception as e:
            print(e)
            return False
    
    def presign(self, bucket: str, object_key: str) -> bool:
        # 生成预签名的GET请求
        pre_result = self.client.presign(
            oss.GetObjectRequest(
                bucket=bucket,  # 指定存储空间名称
                key=object_key,  # 指定对象键名
            )
        )

        # 打印预签名请求的方法、过期时间和URL
        log_with_timestamp(f'method: {pre_result.method},'
              f' expiration: {pre_result.expiration.strftime("%Y-%m-%dT%H:%M:%S.000Z")},'
              f' url: {pre_result.url}'
              )

        return True, pre_result.url