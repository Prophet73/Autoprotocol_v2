import { useEffect, useState } from 'react';
import { logsApi } from '../../api/adminApi';
import { getApiErrorMessage } from '../../utils/errorMessage';
import { useConfirm } from '../../hooks/useConfirm';
import type { ErrorLog, ErrorLogSummary } from '../../api/adminApi';

export default function LogsPage() {
  const { confirm, alert, ConfirmDialog } = useConfirm();
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
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка загрузки логов'));
    } finally {
      setLoading(false);
    }
  };

  const handleCleanup = async (days: number) => {
    if (!(await confirm(`Удалить логи старше ${days} дней?`, { variant: 'danger' }))) return;

    try {
      setCleaning(true);
      const result = await logsApi.cleanup(days);
      await alert(`Удалено записей: ${result.deleted}`);
      await loadData();
    } catch (err) {
      await alert(getApiErrorMessage(err, 'Ошибка очистки'));
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
          <h1 className="text-2xl font-bold text-slate-800">Логи ошибок</h1>
          <p className="text-slate-500 mt-1">Мониторинг ошибок системы ({total})</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleCleanup(7)}
            disabled={cleaning}
            className="px-3 py-2 bg-slate-100 hover:bg-slate-300 disabled:bg-slate-50 text-slate-800 text-sm rounded-lg transition"
          >
            Очистить {'>'}7 дней
          </button>
          <button
            onClick={() => handleCleanup(30)}
            disabled={cleaning}
            className="px-3 py-2 bg-slate-100 hover:bg-slate-300 disabled:bg-slate-50 text-slate-800 text-sm rounded-lg transition"
          >
            Очистить {'>'}30 дней
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200">
            <p className="text-slate-500 text-sm">Всего ошибок</p>
            <p className="text-2xl font-bold text-slate-800">{summary.total_errors}</p>
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200">
            <p className="text-slate-500 text-sm">Сегодня</p>
            <p className="text-2xl font-bold text-red-500">{summary.errors_today}</p>
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200">
            <p className="text-slate-500 text-sm">За неделю</p>
            <p className="text-2xl font-bold text-yellow-600">{summary.errors_this_week}</p>
          </div>
        </div>
      )}

      {/* Stats by type */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200">
            <h3 className="text-sm font-medium text-slate-500 mb-3">По типу ошибки</h3>
            <div className="space-y-2">
              {Object.entries(summary.by_error_type).slice(0, 5).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <code className="text-sm text-slate-600 truncate max-w-[200px]">{type}</code>
                  <span className="text-slate-800 font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200">
            <h3 className="text-sm font-medium text-slate-500 mb-3">По статус-коду</h3>
            <div className="space-y-2">
              {Object.entries(summary.by_status_code).map(([code, count]) => (
                <div key={code} className="flex items-center justify-between">
                  <span className={`text-sm font-mono ${
                    parseInt(code) >= 500 ? 'text-red-500' :
                    parseInt(code) >= 400 ? 'text-yellow-600' : 'text-slate-600'
                  }`}>
                    {code}
                  </span>
                  <span className="text-slate-800 font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-500">{error}</p>
        </div>
      )}

      {/* Logs Table */}
      <div className="bg-white rounded-lg overflow-hidden shadow-sm border border-slate-200">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>Ошибок не найдено</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-600 uppercase">Время</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-600 uppercase">Метод</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-600 uppercase">Endpoint</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-600 uppercase">Код</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-600 uppercase">Тип</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-600 uppercase">Пользователь</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {logs.map((log) => (
                    <tr
                      key={log.id}
                      className="hover:bg-slate-50/50 cursor-pointer"
                      onClick={() => setSelectedLog(log)}
                    >
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-slate-600">
                        {new Date(log.timestamp).toLocaleString('ru-RU')}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                          log.method === 'GET' ? 'bg-green-100 text-green-700' :
                          log.method === 'POST' ? 'bg-blue-100 text-blue-700' :
                          log.method === 'DELETE' ? 'bg-red-100 text-red-700' :
                          'bg-slate-50 text-slate-600'
                        }`}>
                          {log.method}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 max-w-[200px] truncate">
                        {log.endpoint}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`text-sm font-mono ${
                          log.status_code >= 500 ? 'text-red-500' :
                          log.status_code >= 400 ? 'text-yellow-600' : 'text-slate-600'
                        }`}>
                          {log.status_code}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-500 max-w-[150px] truncate">
                        {log.error_type}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-500">
                        {log.user_email || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200">
                <div className="text-sm text-slate-500">
                  Страница {page} из {totalPages}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 bg-slate-50 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed text-slate-800 rounded transition"
                  >
                    Назад
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-3 py-1 bg-slate-50 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed text-slate-800 rounded transition"
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
          <div className="relative bg-white rounded-lg p-6 w-full max-w-2xl shadow-xl border border-slate-200 mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-start justify-between mb-4">
              <h2 className="text-xl font-bold text-slate-800">Детали ошибки #{selectedLog.id}</h2>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-slate-500 hover:text-slate-800"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-500">Время</p>
                  <p className="text-slate-800">{new Date(selectedLog.timestamp).toLocaleString('ru-RU')}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Статус</p>
                  <p className={`font-mono ${
                    selectedLog.status_code >= 500 ? 'text-red-500' : 'text-yellow-600'
                  }`}>
                    {selectedLog.status_code}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Метод</p>
                  <p className="text-slate-800">{selectedLog.method}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Пользователь</p>
                  <p className="text-slate-800">{selectedLog.user_email || 'Аноним'}</p>
                </div>
              </div>

              <div>
                <p className="text-sm text-slate-500 mb-1">Endpoint</p>
                <code className="block bg-slate-100 rounded p-2 text-sm text-blue-600 break-all">
                  {selectedLog.endpoint}
                </code>
              </div>

              <div>
                <p className="text-sm text-slate-500 mb-1">Тип ошибки</p>
                <code className="block bg-slate-100 rounded p-2 text-sm text-red-500">
                  {selectedLog.error_type}
                </code>
              </div>

              <div>
                <p className="text-sm text-slate-500 mb-1">Описание</p>
                <pre className="bg-slate-100 rounded p-3 text-sm text-slate-600 whitespace-pre-wrap overflow-x-auto">
                  {selectedLog.error_detail}
                </pre>
              </div>

              {selectedLog.request_body && (
                <div>
                  <p className="text-sm text-slate-500 mb-1">Тело запроса</p>
                  <pre className="bg-slate-100 rounded p-3 text-sm text-slate-600 whitespace-pre-wrap overflow-x-auto max-h-[200px]">
                    {selectedLog.request_body}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      {ConfirmDialog}
    </div>
  );
}
