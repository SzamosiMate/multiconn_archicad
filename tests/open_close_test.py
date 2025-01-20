
from multi_conn_ac import MultiConn
from dialog_handlers import dialog_handler

m_conn = MultiConn()
m_conn.connect.all()
headers = m_conn.quit.all()

m_conn.open_project.from_header(headers[0], dialog_handler=dialog_handler)

