/**
 * 下载文件辅助函数
 * 
 * 创建隐藏的 <a> 标签触发浏览器下载，支持中文文件名
 */

/**
 * 触发文件下载
 * 
 * @param url - 文件下载 URL
 * @param filename - 文件名（支持中文）
 * 
 * @example
 * ```typescript
 * // 下载附件
 * downloadFile('/api/v1/attachments/123/download', '项目文档.pdf');
 * 
 * // 下载导出文件
 * downloadFile(blobUrl, '任务列表.xlsx');
 * ```
 */
export function downloadFile(url: string, filename: string): void {
  // 创建隐藏的 <a> 标签
  const link = document.createElement('a');
  link.style.display = 'none';
  link.href = url;
  
  // 设置下载文件名
  // 浏览器会自动处理 filename 的编码，支持中文
  link.download = filename;
  
  // 添加到 DOM，触发点击，然后移除
  document.body.appendChild(link);
  link.click();
  
  // 清理：移除 DOM 元素
  document.body.removeChild(link);
  
  // 如果 URL 是 Blob URL，释放内存
  if (url.startsWith('blob:')) {
    window.URL.revokeObjectURL(url);
  }
}
