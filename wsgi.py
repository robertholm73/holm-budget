import app; app.app.run(host='0.0.0.0', port=int(__import__('os').environ.get('PORT', 8000)))
