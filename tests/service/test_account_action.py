from datetime import datetime

import pytest

from account import domain_exception
from account.entity import Account, Card, AccountRecord
from account.service import handler, service_exceptions
from tests.conftest import FakeUnitOfWork, FakeSessionmanager


def setup_account_test(balance, raise_update_failure=False):
    card_num = 1323
    user_id = 17718
    session_manager = FakeSessionmanager()
    session_key = session_manager.set_session(user_id=user_id)
    last_record_index = 387

    account = Account(
        user_id=user_id,
        account_id=1, name='Test account',
        histories=[
            AccountRecord(
                record_index=last_record_index,
                balance=balance,
                action=AccountRecord.DEPOSIT,
                time_at=datetime.utcnow()
            )
        ]
    )

    uow = FakeUnitOfWork(
        cards=[Card(card_num=card_num, user_id=user_id, pin_salt_hash='something')],
        accounts=[account],
        raise_update_failure=raise_update_failure
    )
    return card_num, account.account_id, last_record_index, session_key, uow, session_manager


@pytest.mark.parametrize('amount,balance', [(333, 23223), (3581, 0), (38467, 38467)])
def test_deposit(amount, balance):
    card_num, account_id, last_record_index, session_key, uow, session_manager = setup_account_test(balance)
    account = handler.account_action(
        session_key=session_key,
        account_id=account_id,
        action=AccountRecord.DEPOSIT,
        card_num=card_num,
        uow=uow,
        amount=amount,
        session_manager=session_manager
    )

    assert account.get_balance() == balance + amount
    assert account.histories[-1].record_index == last_record_index + 1


@pytest.mark.parametrize('amount,balance', [(333, 23223), (9, 10), (38467, 38467), (1, 1)])
def test_withdrawal(amount, balance):
    card_num, account_id, last_record_index, session_key, uow, session_manager = setup_account_test(balance)
    account = handler.account_action(
        session_key=session_key,
        account_id=account_id,
        action=AccountRecord.WITHDRAWAL,
        card_num=card_num,
        uow=uow,
        amount=amount,
        session_manager=session_manager
    )

    assert account.get_balance() == balance - amount
    assert account.histories[-1].record_index == last_record_index + 1


@pytest.mark.parametrize('amount,balance', [(2, 1), (1, 0), (100, 99), (124, 71)])
def test_invalid_withdrawal(amount, balance):
    balance = 3289
    card_num, account_id, last_record_index, session_key, uow, session_manager = setup_account_test(balance)
    with pytest.raises(domain_exception.NegativeAccountBalanceException):
        handler.account_action(
            session_key=session_key,
            account_id=account_id,
            action=AccountRecord.WITHDRAWAL,
            card_num=card_num,
            uow=uow,
            amount=balance + 1,
            session_manager=session_manager
        )


def test_invalid_session():
    card_num, account_id, last_record_index, session_key, uow, session_manager = setup_account_test(0)
    with pytest.raises(service_exceptions.InvalidSesionKey):
        handler.account_action(
            session_key=session_key + 'a',
            account_id=account_id,
            action=AccountRecord.DEPOSIT,
            card_num=card_num,
            uow=uow,
            amount=10,
            session_manager=session_manager
        )


def test_invalid_card():
    card_num, account_id, last_record_index, session_key, uow, session_manager = setup_account_test(0)
    with pytest.raises(service_exceptions.InvalidCardNum):
        handler.account_action(
            session_key=session_key,
            account_id=account_id,
            action=AccountRecord.DEPOSIT,
            card_num=card_num + 1,
            uow=uow,
            amount=10,
            session_manager=session_manager
        )


def test_invalid_amount():
    card_num, account_id, last_record_index, session_key, uow, session_manager = setup_account_test(0)
    with pytest.raises(domain_exception.InvalidAmount):
        handler.account_action(
            session_key=session_key,
            account_id=account_id,
            action=AccountRecord.DEPOSIT,
            card_num=card_num,
            uow=uow,
            amount=-1,
            session_manager=session_manager
        )


def test_invalid_action():
    card_num, account_id, last_record_index, session_key, uow, session_manager = setup_account_test(0)
    with pytest.raises(ValueError):
        handler.account_action(
            session_key=session_key,
            account_id=account_id,
            action='some',
            card_num=card_num,
            uow=uow,
            amount=1,
            session_manager=session_manager
        )


@pytest.mark.parametrize('action', [AccountRecord.DEPOSIT, AccountRecord.WITHDRAWAL])
def test_action_record_integrity_failure(action):
    card_num, account_id, last_record_index, session_key, uow, session_manager = setup_account_test(1, True)
    with pytest.raises(service_exceptions.AccountHistoryIntegrityError):
        handler.account_action(
            session_key=session_key,
            account_id=account_id,
            action=action,
            card_num=card_num,
            uow=uow,
            amount=1,
            session_manager=session_manager
        )