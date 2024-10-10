import definitions as defs
import circle_api
circle_api.create_wallet(20, defs.Blockchain.MATIC_AMOY).save('data/wallets/MATIC-AMOY.json')
print('wallets created')


# need to automate this in the future. 
# can change to more wallets  e.g. 50, 100, 200, etc. 
