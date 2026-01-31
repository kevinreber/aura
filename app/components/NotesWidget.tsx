import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { loadNotes, type Note, saveNotes } from '../lib/storage';

interface NotesWidgetProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

export function NotesWidget({ collapsed = false, onToggle }: NotesWidgetProps) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [currentNote, setCurrentNote] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isPreview, setIsPreview] = useState(false);

  useEffect(() => {
    setNotes(loadNotes());
  }, []);

  useEffect(() => {
    if (notes.length > 0) {
      saveNotes(notes);
    }
  }, [notes]);

  const handleAddNote = () => {
    if (!currentNote.trim()) return;

    const newNote: Note = {
      id: Date.now().toString(),
      content: currentNote.trim(),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setNotes((prev) => [newNote, ...prev]);
    setCurrentNote('');
  };

  const handleUpdateNote = (id: string, content: string) => {
    setNotes((prev) =>
      prev.map((note) =>
        note.id === id ? { ...note, content, updatedAt: new Date().toISOString() } : note
      )
    );
    setEditingId(null);
  };

  const handleDeleteNote = (id: string) => {
    setNotes((prev) => prev.filter((note) => note.id !== id));
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 transition-all ${collapsed ? 'p-3' : 'p-4 sm:p-6'}`}
    >
      <div className={`flex items-center justify-between ${collapsed ? 'mb-0' : 'mb-4'}`}>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
          📝 Notes
          {collapsed && notes.length > 0 && (
            <span className="ml-2 text-sm font-normal text-gray-600 dark:text-gray-400">
              {notes.length} note{notes.length !== 1 ? 's' : ''}
            </span>
          )}
        </h2>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          aria-label={collapsed ? 'Expand notes' : 'Collapse notes'}
        >
          <svg
            className={`w-4 h-4 text-gray-500 transition-transform ${collapsed ? '' : 'rotate-180'}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {!collapsed && (
        <div className="space-y-3">
          {/* New Note Input */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Supports Markdown formatting
              </span>
              <button
                onClick={() => setIsPreview(!isPreview)}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                {isPreview ? 'Edit' : 'Preview'}
              </button>
            </div>
            {isPreview ? (
              <div className="min-h-[60px] p-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700/50 text-sm prose dark:prose-invert max-w-none">
                <ReactMarkdown>{currentNote || '*No content yet*'}</ReactMarkdown>
              </div>
            ) : (
              <textarea
                value={currentNote}
                onChange={(e) => setCurrentNote(e.target.value)}
                placeholder="Write a note... (Markdown supported)"
                className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white resize-none"
                rows={3}
              />
            )}
            <button
              onClick={handleAddNote}
              disabled={!currentNote.trim()}
              className="w-full px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Add Note
            </button>
          </div>

          {/* Notes List */}
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {notes.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                No notes yet. Start writing!
              </p>
            ) : (
              notes.slice(0, 5).map((note) => (
                <div key={note.id} className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg group">
                  {editingId === note.id ? (
                    <div className="space-y-2">
                      <textarea
                        defaultValue={note.content}
                        className="w-full px-2 py-1 text-sm border border-gray-200 dark:border-gray-600 rounded focus:ring-1 focus:ring-blue-500 dark:bg-gray-700 dark:text-white resize-none"
                        rows={3}
                        id={`edit-${note.id}`}
                      />
                      <div className="flex space-x-2">
                        <button
                          onClick={() => {
                            const textarea = document.getElementById(
                              `edit-${note.id}`
                            ) as HTMLTextAreaElement;
                            handleUpdateNote(note.id, textarea.value);
                          }}
                          className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="px-2 py-1 text-xs bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded hover:bg-gray-300 dark:hover:bg-gray-500"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="text-sm text-gray-700 dark:text-gray-300 prose dark:prose-invert max-w-none prose-sm">
                        <ReactMarkdown>{note.content}</ReactMarkdown>
                      </div>
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-xs text-gray-400">{formatDate(note.updatedAt)}</span>
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity space-x-2">
                          <button
                            onClick={() => setEditingId(note.id)}
                            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteNote(note.id)}
                            className="text-xs text-red-600 dark:text-red-400 hover:underline"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
