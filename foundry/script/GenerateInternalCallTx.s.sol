// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";

contract D {
    event Hit(string name, address caller, uint256 depth);
    function ping(uint256 depth) external returns (uint256) {
        emit Hit("D", msg.sender, depth);
        return depth;
    }
}

contract C {
    D public d; event Hit(string name, address caller, uint256 depth);
    constructor(address _d) { d = D(_d); }
    function callD(uint256 depth) external returns (uint256) {
        emit Hit("C", msg.sender, depth);
        return d.ping(depth + 1);
    }
}

contract B {
    C public c; event Hit(string name, address caller, uint256 depth);
    constructor(address _c) { c = C(_c); }
    function callC(uint256 depth) external returns (uint256) {
        emit Hit("B", msg.sender, depth);
        return c.callD(depth + 1);
    }
}

contract A {
    B public b; event Hit(string name, address caller, uint256 depth);
    constructor(address _b) { b = B(_b); }
    function kickoff() external returns (uint256) {
        uint256 startDepth = 0;
        emit Hit("A", msg.sender, startDepth);
        return b.callC(startDepth + 1);
    }
}

contract GenerateInternalCallTx is Script {
    function run() external {
        vm.startBroadcast();
        D d = new D();
        C c = new C(address(d));
        B b = new B(address(c));
        A a = new A(address(b));
        uint256 ret = a.kickoff();
        console2.log("Final depth:", ret);
        vm.stopBroadcast();
    }
}

