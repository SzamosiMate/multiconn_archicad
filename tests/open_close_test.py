
from multi_conn_ac import MultiConn, ArchiCadID
from dialog_handlers import start_handling_dialogs
from multi_conn_ac.basic_types import TeamworkCredentials

m_conn = MultiConn()
m_conn.connect.all()
headers = m_conn.quit.all()

print(headers[0])

tw = TeamworkCredentials(username='szamosi.mate.iroda',
                         password='*******')

m_conn.open_project.with_teamwork_credentials(headers[0], teamwork_credentials=tw, dialog_handler=start_handling_dialogs)

