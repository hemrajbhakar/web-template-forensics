import React from 'react';

function ComplexComponent({ 
  title = "Default Title",
  items = [],
  onAction,
  style = {},
  ...otherProps 
}) {
  const [isOpen, setIsOpen] = React.useState(false);
  const count = items.length;

  return (
    <div className="complex-component" style={style} {...otherProps}>
      <header className={`header ${isOpen ? 'open' : 'closed'}`}>
        <h1>{title}</h1>
        <button 
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? 'Close panel' : 'Open panel'}
        >
          {isOpen ? '▼' : '▲'}
        </button>
      </header>

      {isOpen && (
        <div className="content">
          <p className="summary">
            Total items: <strong>{count}</strong>
          </p>
          
          <div className="items-list">
            <h1>Items ({items.length})</h1>
            <div className="list">
              {items.map((item, index) => (
                <div key={index} className="item">
                  <span>{item.name}</span>
                  <div className="actions">
                    <button onClick={() => onAction(item.id, 'edit')}>
                      Edit
                    </button>
                    <button onClick={() => onAction(item.id, 'delete')}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {count === 0 && (
            <div className="empty-state">
              <EmptyIcon size={48} />
              <p>No items found</p>
            </div>
          )}
        </div>
      )}

      <footer>
        <small>Last updated: {new Date().toLocaleDateString()}</small>
      </footer>
    </div>
  );
}

function ItemsList({ items = [], onAction }) {
  return (
    <div className="items-list">
      <h1>Items ({items.length})</h1>
      <div className="list">
        {items.map((item, index) => (
          <div key={index} className="item">
            <span>{item.name}</span>
            <div className="actions">
              <button onClick={() => onAction(item.id, 'edit')}>
                Edit
              </button>
              <button onClick={() => onAction(item.id, 'delete')}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
      <footer>
        <small>Updated: {new Date().toLocaleDateString()}</small>
      </footer>
    </div>
  );
}

export default ComplexComponent; 