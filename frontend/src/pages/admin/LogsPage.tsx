import { useEffect, useState } from 'react';
import { logsApi } from '../../api/adminApi';
import type { ErrorLog, ErrorLogSummary } from '../../api/adminApi';

export default function LogsPage() {
  const [logs, setLogs] = useState<ErrorLog[]>([]);
  const [summary, setSummary] = useState<ErrorLogSummary | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedLog, setSelectedLog] = useState<ErrorLog | null>(null);
  const [cleaning, setCleaning] = useState(false);

  useEffect(() => {
    loadData();
  }, [page]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [logsResponse, summaryData] = await Promise.all([
        logsApi.list({ page, page_size: pageSize }),
        logsApi.getSummary(),
      ]);
      setLogs(logsResponse.logs);
      setTotal(logsResponse.total);
      setSummary(summaryData);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки логов');
    } finally {
      setLoading(false);
    }
  };

  const handleCleanup = async (days: number) => {
    if (!confirm(`Удалить логи старше ${days} дней?`)) return;

    try {
      setCleaning(true);
      const result = await logsApi.cleanup(days);
      alert(`Удалено записей: ${result.deleted}`);
      await loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка очистки');
    } finally {
      setCleaning(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Логи ошибок</h1>
          <p className="text-gray-400 mt-1">Мониторинг ошибок системы ({total})</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleCleanup(7)}
            disabled={cleaning}
            className="px-3 py-2 bg-gray-600 hover:bg-gray-500 disabled:bg-gray-700 text-white text-sm rounded-lg transition"
          >
            Очистить {'>'}7 дней
          </button>
          <button
            onClick={() => handleCleanup(30)}
            disabled={cleaning}
            className="px-3 py-2 bg-gray-600 hover:bg-gray-500 disabled:bg-gray-700 text-white text-sm rounded-lg transition"
          >
            Очистить {'>'}30 дней
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-gray-400 text-sm">Всего ошибок</p>
            <p className="text-2xl font-bold text-white">{summary.total_errors}</p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-gray-400 text-sm">Сегодня</p>
            <p className="text-2xl font-bold text-red-400">{summary.errors_today}</p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <p className="text-gray-400 text-sm">За неделю</p>
            <p className="text-2xl font-bold text-yellow-400">{summary.errors_this_week}</p>
          </div>
        </div>
      )}

      {/* Stats by type */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-800 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-400 mb-3">По типу ошибки</h3>
            <div className="space-y-2">
              {Object.entries(summary.by_error_type).slice(0, 5).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <code className="text-sm text-gray-300 truncate max-w-[200px]">{type}</code>
                  <span className="text-white font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-400 mb-3">По статус-коду</h3>
            <div className="space-y-2">
              {Object.entries(summary.by_status_code).map(([code, count]) => (
                <div key={code} className="flex items-center justify-between">
                  <span className={`text-sm font-mono ${
                    parseInt(code) >= 500 ? 'text-red-400' :
                    parseInt(code) >= 400 ? 'text-yellow-400' : 'text-gray-300'
                  }`}>
                    {code}
                  </span>
                  <span className="text-white font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-900/50 border border-red-500 rounded-lg p-4">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Logs Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>Ошибок не найдено</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">Время</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">Метод</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">Endpoint</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">Код</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">Тип</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">Пользователь</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {logs.map((log) => (
                    <tr
                      key={log.id}
                      className="hover:bg-gray-700/50 cursor-pointer"
                      onClick={() => setSelectedLog(log)}
                    >
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">
                        {new Date(log.timestamp).toLocaleString('ru-RU')}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                          log.method === 'GET' ? 'bg-green-900 text-green-300' :
                          log.method === 'POST' ? 'bg-blue-900 text-blue-300' :
                          log.method === 'DELETE' ? 'bg-red-900 text-red-300' :
                          'bg-gray-700 text-gray-300'
                        }`}>
                          {log.method}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-300 max-w-[200px] truncate">
                        {log.endpoint}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`text-sm font-mono ${
                          log.status_code >= 500 ? 'text-red-400' :
                          log.status_code >= 400 ? 'text-yellow-400' : 'text-gray-300'
                        }`}>
                          {log.status_code}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-400 max-w-[150px] truncate">
                        {log.error_type}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-400">
                        {log.user_email || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-700">
                <div className="text-sm text-gray-400">
                  Страница {page} из {totalPages}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition"
                  >
                    Назад
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition"
                  >
                    Вперед
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Detail Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setSelectedLog(null)} />
          <div className="relative bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-start justify-between mb-4">
              <h2 className="text-xl font-bold text-white">Детали ошибки #{selectedLog.id}</h2>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-gray-400 hover:text-white"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-400">Время</p>
                  <p className="text-white">{new Date(selectedLog.timestamp).toLocaleString('ru-RU')}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Статус</p>
                  <p className={`font-mono ${
                    selectedLog.status_code >= 500 ? 'text-red-400' : 'text-yellow-400'
                  }`}>
                    {selectedLog.status_code}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Метод</p>
                  <p className="text-white">{selectedLog.method}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Пользователь</p>
                  <p className="text-white">{selectedLog.user_email || 'Аноним'}</p>
                </div>
              </div>

              <div>
                <p className="text-sm text-gray-400 mb-1">Endpoint</p>
                <code className="block bg-gray-900 rounded p-2 text-sm text-blue-400 break-all">
                  {selectedLog.endpoint}
                </code>
              </div>

              <div>
                <p className="text-sm text-gray-400 mb-1">Тип ошибки</p>
                <code className="block bg-gray-900 rounded p-2 text-sm text-red-400">
                  {selectedLog.error_type}
                </code>
              </div>

              <div>
                <p className="text-sm text-gray-400 mb-1">Описание</p>
                <pre className="bg-gray-900 rounded p-3 text-sm text-gray-300 whitespace-pre-wrap overflow-x-auto">
                  {selectedLog.error_detail}
                </pre>
              </div>

              {selectedLog.request_body && (
                <div>
                  <p className="text-sm text-gray-400 mb-1">Тело запроса</p>
                  <pre className="bg-gray-900 rounded p-3 text-sm text-gray-300 whitespace-pre-wrap overflow-x-auto max-h-[200px]">
                    {selectedLog.request_body}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
