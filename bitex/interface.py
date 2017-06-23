# Import Built-Ins
import logging
import warnings

# Import Third-Party

# Import Homebrew
from .pairs import PairFormatter
from .exceptions import UnsupportedPairError, EmptySupportedPairListWarning
from .rest import BitfinexREST, BittrexREST, BitstampREST, BTCEREST, BterREST
from .rest import CCEXREST, CoincheckREST, CryptopiaREST
from .rest import HitBTCREST, KrakenREST, OKCoinREST, PoloniexREST
from .rest import QuadrigaCXREST, RockTradingREST, VaultoroREST
# Init Logging Facilities
log = logging.getLogger(__name__)


class Interface:
    def __init__(self, *, name, rest_api):
        self.REST = rest_api
        self.name = name
        try:
            self._supported_pairs = self._get_supported_pairs()
        except NotImplementedError:
            self._supported_pairs = None

    @property
    def supported_pairs(self):
        return self._supported_pairs

    def _get_supported_pairs(self):
        """Generate a list of supported pairs.

        Queries the API for a list of supported pairs and returns this as a
        list.

        Raises a NotImplementedError by default and needs to be overridden in
        child classes.

        :raises: NotImplementedError
        """
        raise NotImplementedError

    def is_supported(self, pair):
        """Checks if the given pair is present in self._supported_pairs.

        Input can either be a string or a PairFormatter Obj (or child thereof).
        If the latter two, we'll call the format_for() method with the Interface's
        name attribute to acquire proper formatting.
        Since str.format_for() doesn't raise an error if a string isnt used,
        this works for both PairFormatter objects and strings.
        :param pair: Str, or PairFormatter Object
        :return: Bool
        """
        pair = (PairFormatter.format_for(pair, self.name) if
                isinstance(pair, PairFormatter) else
                pair)

        if pair in self.supported_pairs:
            return True
        else:
            return False

    def request(self, verb, endpoint, authenticate=False, **req_kwargs):
        """Query the API and return its result.

        :param verb: HTTP verb (GET, PUT, DELETE, etc)
        :param endpoint: Str
        :param authenticate: Bool, whether to call private_query or public_query
                             method.
        :param req_kwargs: Kwargs to pass to _query / requests.request()
        :raise: UnsupportedPairError
        :return: requests.Response() Obj
        """

        if authenticate:
            return self.REST.private_query(verb, endpoint, **req_kwargs)
        else:
            return self.REST.public_query(verb, endpoint, **req_kwargs)


class RESTInterface(Interface):
    def __init__(self, name, rest_api):
        super(RESTInterface, self).__init__(name=name, rest_api=rest_api)

    # Public Endpoints
    def ticker(self, pair, *args, **kwargs):
        raise NotImplementedError

    def order_book(self, pair, *args, **kwargs):
        raise NotImplementedError

    def trades(self, pair, *args, **kwargs):
        raise NotImplementedError

    # Private Endpoints
    def ask(self, pair, price, size, *args, **kwargs):
        raise NotImplementedError

    def bid(self, pair, price, size, *args, **kwargs):
        raise NotImplementedError

    def order_status(self, order_id, *args, **kwargs):
        raise NotImplementedError

    def open_orders(self, *args, **kwargs):
        raise NotImplementedError

    def cancel_order(self, *order_ids, **kwargs):
        raise NotImplementedError

    def wallet(self, currency, *args, **kwargs):
        raise NotImplementedError


class Bitfinex(RESTInterface):
    def __init__(self, **APIKwargs):
        super(Bitfinex, self).__init__('Bitfinex', BitfinexREST(**APIKwargs))

    def request(self, endpoint, authenticate=False, **req_kwargs):
        if not authenticate:
            return super(Bitfinex, self).request('GET', endpoint,
                                                 authenticate=authenticate,
                                          **req_kwargs)
        else:
            return super(Bitfinex, self).request('POST', endpoint,
                                                 authenticate=authenticate,
                                                 **req_kwargs)

    def _get_supported_pairs(self):
        return self.symbols()

    ###############
    # Basic Methods
    ###############
    def ticker(self, pair):
        self.is_supported(pair)
        return self.request('pubticker/%s' % pair.format_for(self.name))

    def order_book(self, pair, **endpoint_kwargs):
        self.is_supported(pair)
        return self.request('book/%s' % pair.format_for(self.name),
                            params=endpoint_kwargs)

    def trades(self, pair, **endpoint_kwargs):
        self.is_supported(pair)
        return self.request('trades/%s' % pair.format_for(self.name),
                            params=endpoint_kwargs)

    def ask(self, pair, price, size, *args, **kwargs):
        return self._place_order(pair, price, size, 'sell', **kwargs)

    def bid(self, pair, price, size, *args, **kwargs):
        return self._place_order(pair, price, size, 'buy', **kwargs)

    def _place_order(self, pair, price, size, side, **kwargs):
        payload = {'symbol': pair.format_for(self.name), 'price': price,
                   'amount': size, 'side': side, 'type': 'exchange-limit'}
        payload.update(kwargs)
        return self.new_order(pair, **payload)

    def order_status(self, order_id, *args, **kwargs):
        return self.request('order/status', authenticate=True,
                            params={'order_id': order_id})

    def open_orders(self, *args, **kwargs):
        return self.active_orders(*args, **kwargs)

    def cancel_order(self, order_id, **kwargs):
        return self.request('order/cancel', authenticate=True,
                            params={'order_id': order_id})

    def wallet(self, *args, **kwargs):
        return self.balances()


    ###########################
    # Exchange Specific Methods
    ###########################
    def symbols(self, verbose=False):
        if verbose:
            return self.request('symbols_details')
        else:
            return self.request('symbols')

    def symbols_details(self,):
        return self.request('symbols_details')

    def stats(self, pair):
        self.is_supported(pair)
        return self.request('stats/%s' % pair.format_for(self.name))

    def lends(self, currency, **endpoint_kwargs):
        return self.request('lends/%s' % currency,
                            params=endpoint_kwargs)

    def funding_book(self, currency, **endpoint_kwargs):
        return self.request('lendbook/%s' % currency,
                            params=endpoint_kwargs)

    def account_info(self):
        return self.request('account_infos', authenticate=True)

    def account_fees(self):
        return self.request('account_fees', authenticate=True)

    def summary(self):
        return self.request('summary', authenticate=True)

    def deposit(self, **endpoint_kwargs):
        return self.request('deposit', authenticate=True,
                            params=endpoint_kwargs)

    def key_info(self):
        return self.request('key_info', authenticate=True)

    def margin_info(self):
        return self.request('margin_info', authenticate=True)

    def balances(self):
        return self.request('balances', authenticate=True)

    def transfer(self, **endpoint_kwargs):
        return self.request('transfer', authenticate=True,
                            params=endpoint_kwargs)

    def withdrawal(self, **endpoint_kwargs):
        return self.request('withdraw', authenticate=True,
                            params=endpoint_kwargs)

    def new_order(self, pair, **endpoint_kwargs):
        self.is_supported(pair)
        payload = {'symbol': pair.format_for(self.name)}
        payload.update(endpoint_kwargs)
        return self.request('order/new', authenticate=True,
                            params=payload)

    def multiple_new_orders(self, *orders):
        raise NotImplementedError

    def cancel_multiple_orders(self, *order_ids):
        return self.request('order/cancel/multi', authenticate=True,
                            params={'order_ids': order_ids})

    def cancel_all_orders(self):
        return self.request('order/cancel/all', authenticate=True)

    def replace_order(self, **endpoint_kwargs):
        return self.request('order/cancel/replace', authenticate=True,
                            params=endpoint_kwargs)

    def active_orders(self, *args, **kwargs):
        return self.request('orders', authenticate=True)

    def active_positions(self):
        return self.request('positions', authenticate=True)

    def claim_position(self, **endpoint_kwargs):
        return self.request('position/claim', authenticate=True,
                            params=endpoint_kwargs)

    def balance_history(self, **endpoint_kwargs):
        return self.request('history', authenticate=True,
                            params=endpoint_kwargs)

    def deposit_withdrawal_history(self, **endpoint_kwargs):
        return self.request('history/movement', authenticate=True,
                            params=endpoint_kwargs)

    def past_trades(self, pair, **endpoint_kwargs):
        self.is_supported(pair)
        payload = {'symbol': pair.format_for(self.name)}
        payload.update(endpoint_kwargs)
        return self.request('mytrades', authenticate=True,
                            params=payload)

    def new_offer(self, **endpoint_kwargs):
        return self.request('offer/new', authenticate=True,
                            params=endpoint_kwargs)

    def cancel_offer(self, **endpoint_kwargs):
        return self.request('offer/cancel', authenticate=False,
                            params=endpoint_kwargs)

    def offer_status(self, **endpoint_kwargs):
        return self.request('offer/status', authenticate=True,
                            params=endpoint_kwargs)

    def active_credits(self, **endpoint_kwargs):
        return self.request('credits', authenticate=True,
                            params=endpoint_kwargs)

    def offers(self, **endpoint_kwargs):
        return self.request('offers', authenticate=True,
                            params=endpoint_kwargs)

    def taken_funds(self, **endpoint_kwargs):
        return self.request('taken_funds', authenticate=True,
                            params=endpoint_kwargs)

    def unused_taken_funds(self, **endpoint_kwargs):
        return self.request('unused_taken_funds', authenticate=True,
                            params=endpoint_kwargs)

    def total_taken_funds(self, **endpoint_kwargs):
        return self.request('total_taken_funds', authenticate=True,
                            params=endpoint_kwargs)

    def close_funding(self, **endpoint_kwargs):
        return self.request('funding/close', authenticate=True,
                            params=endpoint_kwargs)

    def basket_manage(self, **endpoint_kwargs):
        return self.request('basket_manage', authenticate=True,
                            params=endpoint_kwargs)

class Bitstamp(RESTInterface):
    def __init__(self, **APIKwargs):
        super(Bitstamp, self).__init__('Bitstamp', BitstampREST(**APIKwargs))


class Bittrex(RESTInterface):
    def __init__(self, **APIKwargs):
        super(Bittrex, self).__init__('Bittrex', BittrexREST(**APIKwargs))


class BTCE(RESTInterface):
    def __init__(self, **APIKwargs):
        super(BTCE, self).__init__('BTC-E', BTCEREST(**APIKwargs))


class Bter(RESTInterface):
    def __init__(self, **APIKwargs):
        super(Bter, self).__init__('Bter', BterREST(**APIKwargs))


class CCEX(RESTInterface):
    def __init__(self, **APIKwargs):
        super(CCEX, self).__init__('C-CEX', CCEXREST(**APIKwargs))


class CoinCheck(RESTInterface):
    def __init__(self, **APIKwargs):
        super(CoincheckREST, self).__init__('CoinCheck',
                                            CoincheckREST(**APIKwargs))


class Cryptopia(RESTInterface):
    def __init__(self, **APIKwargs):
        super(Cryptopia, self).__init__('Cryptopia', CryptopiaREST(**APIKwargs))


class HitBTC(RESTInterface):
    def __init__(self, **APIKwargs):
        super(HitBTC, self).__init__('HitBTC', HitBTCREST(**APIKwargs))


class Kraken(RESTInterface):
    def __init__(self, **APIKwargs):
        super(Kraken, self).__init__('Kraken', KrakenREST(**APIKwargs))


class OKCoin(RESTInterface):
    def __init__(self, **APIKwargs):
        super(OKCoin, self).__init__('OKCoin', OKCoinREST(**APIKwargs))


class Poloniex(RESTInterface):
    def __init__(self, **APIKwargs):
        super(Poloniex, self).__init__('Poloniex', PoloniexREST(**APIKwargs))


class QuadrigaCX(RESTInterface):
    def __init__(self, **APIKwargs):
        super(QuadrigaCX, self).__init__('QuadrigaCX',
                                         QuadrigaCXREST(**APIKwargs))


class TheRockTrading(RESTInterface):
    def __init__(self, **APIKwargs):
        super(TheRockTrading, self).__init__('The Rock Trading Ltd.',
                                             RockTradingREST(**APIKwargs))


class Vaultoro(RESTInterface):
    def __init__(self, **APIKwargs):
        super(Vaultoro, self).__init__('Vaultoro', VaultoroREST(**APIKwargs))
