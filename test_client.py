import asyncio

from aioagi.client import AGIClientSession
from aioagi.parser import AGIMessage, AGICode


async def test_request():
    headers = {
        'agi_accountcode': 'incoming-trunk-70',
        'agi_callerid': '01636209692',
        'agi_calleridname': '01636209692',
        'agi_callingani2': '0',
        'agi_callingpres': '0',
        'agi_callingtns': '0',
        'agi_callington': '0',
        'agi_channel': 'PJSIP/sipgate_trunk-00000145',
        'agi_context': 'subCheckBlacklist',
        'agi_dnid': '123456789',
        'agi_enhanced': '0.0',
        'agi_extension': 's',
        'agi_language': 'en',
        'agi_network': 'yes',
        'agi_priority': '9',
        'agi_rdnis': 'unknown',
        'agi_request': 'agi://localhost/',
        'agi_threadid': '139737013024512',
        'agi_type': 'PJSIP',
        'agi_uniqueid': 'asterisk-1719409791.550',
        'agi_version': 'certified-18.9-cert8'
    }
    async with AGIClientSession(headers=headers) as session:
        async with session.sip('agi://localhost:4573/') as response:
            async for message in response:
                print(message)
                await response.send(AGIMessage(AGICode.OK, '0', {}))


asyncio.run(test_request())
