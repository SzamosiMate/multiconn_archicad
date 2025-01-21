
from multi_conn_ac import MultiConn
from dialog_handlers import start_handling_dialogs

m_conn = MultiConn()
m_conn.connect.all()
headers = m_conn.quit.all()

m_conn.open_project.from_header(headers[0], dialog_handler=start_handling_dialogs)

