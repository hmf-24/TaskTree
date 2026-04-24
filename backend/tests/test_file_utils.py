"""
文件工具函数单元测试
"""

import pytest
from backend.app.utils.file_utils import (
    validate_file_type,
    validate_file_size,
    sanitize_filename,
    generate_unique_filename,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE
)


class TestValidateFileType:
    """测试文件类型验证函数"""
    
    def test_valid_document_types(self):
        """测试有效的文档类型"""
        for ext in ["doc", "docx", "pdf", "txt", "md"]:
            is_valid, msg = validate_file_type(f"test.{ext}")
            assert is_valid is True
            assert msg == "文件类型有效"
    
    def test_valid_image_types(self):
        """测试有效的图片类型"""
        for ext in ["jpg", "jpeg", "png", "gif"]:
            is_valid, msg = validate_file_type(f"image.{ext}")
            assert is_valid is True
            assert msg == "文件类型有效"
    
    def test_valid_archive_types(self):
        """测试有效的压缩包类型"""
        for ext in ["zip", "rar"]:
            is_valid, msg = validate_file_type(f"archive.{ext}")
            assert is_valid is True
            assert msg == "文件类型有效"
    
    def test_valid_office_types(self):
        """测试有效的办公文档类型"""
        for ext in ["xls", "xlsx", "ppt", "pptx"]:
            is_valid, msg = validate_file_type(f"document.{ext}")
            assert is_valid is True
            assert msg == "文件类型有效"
    
    def test_case_insensitive(self):
        """测试扩展名不区分大小写"""
        is_valid, msg = validate_file_type("test.PDF")
        assert is_valid is True
        
        is_valid, msg = validate_file_type("test.JpG")
        assert is_valid is True
    
    def test_invalid_file_type(self):
        """测试不支持的文件类型"""
        is_valid, msg = validate_file_type("malicious.exe")
        assert is_valid is False
        assert "不支持的文件类型" in msg
        assert "exe" in msg
    
    def test_empty_filename(self):
        """测试空文件名"""
        is_valid, msg = validate_file_type("")
        assert is_valid is False
        assert "文件名不能为空" in msg
    
    def test_no_extension(self):
        """测试没有扩展名的文件"""
        is_valid, msg = validate_file_type("noextension")
        assert is_valid is False
        assert "文件必须有扩展名" in msg


class TestValidateFileSize:
    """测试文件大小验证函数"""
    
    def test_valid_small_file(self):
        """测试小文件（1KB）"""
        is_valid, msg = validate_file_size(1024)
        assert is_valid is True
        assert msg == "文件大小有效"
    
    def test_valid_medium_file(self):
        """测试中等文件（10MB）"""
        is_valid, msg = validate_file_size(10 * 1024 * 1024)
        assert is_valid is True
        assert msg == "文件大小有效"
    
    def test_valid_max_size_file(self):
        """测试最大允许大小（50MB）"""
        is_valid, msg = validate_file_size(MAX_FILE_SIZE)
        assert is_valid is True
        assert msg == "文件大小有效"
    
    def test_file_just_under_limit(self):
        """测试刚好低于限制的文件"""
        is_valid, msg = validate_file_size(MAX_FILE_SIZE - 1)
        assert is_valid is True
        assert msg == "文件大小有效"
    
    def test_file_exceeds_limit(self):
        """测试超过大小限制的文件"""
        is_valid, msg = validate_file_size(MAX_FILE_SIZE + 1)
        assert is_valid is False
        assert "文件大小超过限制" in msg
        assert "50MB" in msg
    
    def test_very_large_file(self):
        """测试非常大的文件（100MB）"""
        is_valid, msg = validate_file_size(100 * 1024 * 1024)
        assert is_valid is False
        assert "文件大小超过限制" in msg
    
    def test_zero_size_file(self):
        """测试零大小文件"""
        is_valid, msg = validate_file_size(0)
        assert is_valid is False
        assert "文件大小无效" in msg
    
    def test_negative_size(self):
        """测试负数大小"""
        is_valid, msg = validate_file_size(-1)
        assert is_valid is False
        assert "文件大小无效" in msg


class TestSanitizeFilename:
    """测试文件名清理函数"""
    
    def test_clean_filename(self):
        """测试已经干净的文件名"""
        result = sanitize_filename("document.pdf")
        assert result == "document.pdf"
    
    def test_filename_with_spaces(self):
        """测试包含空格的文件名"""
        result = sanitize_filename("my document file.pdf")
        assert result == "my_document_file.pdf"
    
    def test_filename_with_special_chars(self):
        """测试包含特殊字符的文件名"""
        result = sanitize_filename("file@#$%name!.txt")
        assert result == "filename.txt"
    
    def test_filename_with_chinese(self):
        """测试包含中文的文件名"""
        result = sanitize_filename("测试文档.pdf")
        assert result == "测试文档.pdf"
    
    def test_filename_with_mixed_content(self):
        """测试混合内容的文件名"""
        result = sanitize_filename("项目 报告 2024!@#.docx")
        assert result == "项目_报告_2024.docx"
    
    def test_filename_with_multiple_spaces(self):
        """测试多个连续空格"""
        result = sanitize_filename("file   name.txt")
        assert result == "file_name.txt"
    
    def test_filename_with_path_separators(self):
        """测试包含路径分隔符的文件名"""
        result = sanitize_filename("../../etc/passwd.txt")
        assert result == "etcpasswd.txt"
    
    def test_empty_filename(self):
        """测试空文件名"""
        result = sanitize_filename("")
        assert result == "unnamed"
    
    def test_only_special_chars(self):
        """测试只包含特殊字符的文件名"""
        result = sanitize_filename("@#$%.txt")
        assert result == "unnamed.txt"
    
    def test_no_extension(self):
        """测试没有扩展名的文件名"""
        result = sanitize_filename("document")
        assert result == "document"
    
    def test_filename_with_underscores_and_hyphens(self):
        """测试包含下划线和连字符的文件名"""
        result = sanitize_filename("my-file_name.pdf")
        assert result == "my-file_name.pdf"


class TestGenerateUniqueFilename:
    """测试唯一文件名生成函数"""
    
    def test_generates_unique_filenames(self):
        """测试生成的文件名是唯一的"""
        filename1 = generate_unique_filename("test.pdf")
        filename2 = generate_unique_filename("test.pdf")
        assert filename1 != filename2
    
    def test_contains_timestamp(self):
        """测试包含时间戳"""
        result = generate_unique_filename("test.pdf")
        # 时间戳格式：YYYYMMDD_HHMMSS
        assert len(result.split("_")) >= 3
        timestamp_part = result.split("_")[0]
        assert len(timestamp_part) == 8  # YYYYMMDD
        assert timestamp_part.isdigit()
    
    def test_contains_uuid(self):
        """测试包含 UUID"""
        result = generate_unique_filename("test.pdf")
        parts = result.split("_")
        # UUID 部分应该是第二个部分（最多8位）
        assert len(parts) >= 3
        uuid_part = parts[1]
        assert len(uuid_part) <= 8
        assert len(uuid_part) > 0
    
    def test_contains_original_filename(self):
        """测试包含原始文件名"""
        result = generate_unique_filename("document.pdf")
        assert result.endswith("document.pdf")
    
    def test_sanitizes_original_filename(self):
        """测试清理原始文件名"""
        result = generate_unique_filename("my file!@#.pdf")
        assert result.endswith("my_file.pdf")
    
    def test_preserves_extension(self):
        """测试保留文件扩展名"""
        result = generate_unique_filename("test.docx")
        assert result.endswith(".docx")
    
    def test_handles_chinese_filename(self):
        """测试处理中文文件名"""
        result = generate_unique_filename("测试文档.pdf")
        assert "测试文档.pdf" in result
    
    def test_format_structure(self):
        """测试文件名格式结构"""
        result = generate_unique_filename("test.pdf")
        # 格式应该是：timestamp_uuid_filename
        parts = result.split("_")
        assert len(parts) >= 3
        # 最后一部分应该包含原始文件名
        assert "test.pdf" in "_".join(parts[2:])
