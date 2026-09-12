// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable2Step, Ownable} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Base64} from "@openzeppelin/contracts/utils/Base64.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

/// @title Crypto Cougars
/// @notice Local-only ERC-721 implementation of the reset-on-mint decaying-price mechanism.
/// @dev Trait seeds are deterministic and predictable, not secure randomness.
contract CryptoCougars is ERC721, Ownable2Step, ReentrancyGuard {
    using Strings for uint256;

    uint256 public constant MAX_SUPPLY = 10_000;
    bytes32 public constant COLLECTION_SEED = keccak256("CRYPTO_COUGARS_ORIGINAL_COLLECTION_V1");

    uint256 public startPrice = 0.1 ether;
    uint256 public floorPrice = 0.0001 ether;
    uint256 public decayPerBlock = 0.003 ether;
    uint256 public lastResetBlock;

    uint256 internal _nextTokenId;
    mapping(uint256 tokenId => uint256 seed) public seeds;

    error SoldOut();
    error InsufficientPayment(uint256 required, uint256 supplied);
    error InvalidPriceConfiguration();
    error RefundFailed();
    error WithdrawalFailed();

    event Minted(address indexed to, uint256 indexed tokenId, uint256 price, uint256 seed);
    event PriceReset(uint256 indexed blockNumber);
    event PricesUpdated(uint256 startPrice, uint256 floorPrice, uint256 decayPerBlock);
    event Withdrawal(address indexed recipient, uint256 amount);

    constructor() ERC721("Crypto Cougars", "COUGAR") Ownable(msg.sender) {
        lastResetBlock = block.number;
    }

    function totalSupply() public view returns (uint256) {
        return _nextTokenId;
    }

    function currentPrice() public view returns (uint256) {
        uint256 blocksSinceReset = block.number - lastResetBlock;
        uint256 drop = startPrice - floorPrice;

        if (blocksSinceReset >= _ceilDiv(drop, decayPerBlock)) {
            return floorPrice;
        }

        return startPrice - (decayPerBlock * blocksSinceReset);
    }

    function blocksToFloor() public view returns (uint256) {
        uint256 blocksSinceReset = block.number - lastResetBlock;
        uint256 totalBlocks = _ceilDiv(startPrice - floorPrice, decayPerBlock);
        return blocksSinceReset >= totalBlocks ? 0 : totalBlocks - blocksSinceReset;
    }

    function mint() external payable nonReentrant returns (uint256 tokenId) {
        tokenId = _nextTokenId;
        if (tokenId >= MAX_SUPPLY) revert SoldOut();

        uint256 price = currentPrice();
        if (msg.value < price) revert InsufficientPayment(price, msg.value);

        _nextTokenId = tokenId + 1;
        uint256 seed = uint256(keccak256(abi.encode(COLLECTION_SEED, tokenId)));
        seeds[tokenId] = seed;

        lastResetBlock = block.number;
        emit PriceReset(block.number);

        _safeMint(msg.sender, tokenId);

        uint256 refund = msg.value - price;
        if (refund != 0) {
            (bool refunded, ) = msg.sender.call{value: refund}("");
            if (!refunded) revert RefundFailed();
        }

        emit Minted(msg.sender, tokenId, price, seed);
    }

    function traitsOf(
        uint256 tokenId
    ) public view returns (uint8 coat, uint8 eyes, uint8 accessory, uint8 background, bool star) {
        _requireOwned(tokenId);
        uint256 seed = seeds[tokenId];
        coat = uint8(seed % 6);
        eyes = uint8((seed >> 32) % 5);
        accessory = uint8((seed >> 64) % 6);
        background = uint8((seed >> 96) % 6);
        star = ((seed >> 128) % 10) == 0;
    }

    function setPrices(uint256 newStart, uint256 newFloor, uint256 newDecay) external onlyOwner {
        if (newStart <= newFloor || newDecay == 0) revert InvalidPriceConfiguration();

        startPrice = newStart;
        floorPrice = newFloor;
        decayPerBlock = newDecay;
        lastResetBlock = block.number;

        emit PricesUpdated(newStart, newFloor, newDecay);
        emit PriceReset(block.number);
    }

    function withdraw() external onlyOwner nonReentrant {
        address recipient = owner();
        uint256 amount = address(this).balance;
        (bool sent, ) = recipient.call{value: amount}("");
        if (!sent) revert WithdrawalFailed();
        emit Withdrawal(recipient, amount);
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        (uint8 coat, uint8 eye, uint8 accessory, uint8 background, bool star) = traitsOf(tokenId);

        string memory image = _renderSVG(tokenId, coat, eye, accessory, background, star);
        string memory attributes = string.concat(
            '[{"trait_type":"Coat","value":"',
            _coatName(coat),
            '"},{"trait_type":"Eyes","value":"',
            _eyeName(eye),
            '"},{"trait_type":"Accessory","value":"',
            _accessoryName(accessory),
            '"},{"trait_type":"Habitat","value":"',
            _backgroundName(background),
            '"},{"trait_type":"Star","value":"',
            star ? "Yes" : "No",
            '"}]'
        );
        string memory json = string.concat(
            '{"name":"Crypto Cougar #',
            tokenId.toString(),
            '","description":"An original, fully on-chain Crypto Cougar. Deterministic traits; no claim of secure randomness.","image":"data:image/svg+xml;base64,',
            Base64.encode(bytes(image)),
            '","attributes":',
            attributes,
            "}"
        );
        return string.concat("data:application/json;base64,", Base64.encode(bytes(json)));
    }

    function _renderSVG(
        uint256 tokenId,
        uint8 coat,
        uint8 eye,
        uint8 accessory,
        uint8 background,
        bool star
    ) internal pure returns (string memory) {
        string memory fur = _coatColor(coat);
        string memory iris = _eyeColor(eye);
        string memory backdrop = _backgroundColor(background);
        string memory adornment = _accessorySVG(accessory);
        string memory starMark = star
            ? '<path d="M452 48l9 20 22 2-17 14 5 22-19-12-19 12 5-22-17-14 22-2z" fill="#ffd34d" stroke="#241408" stroke-width="5"/>'
            : "";

        return
            string.concat(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="Crypto Cougar #',
                tokenId.toString(),
                '">',
                '<rect width="512" height="512" rx="48" fill="',
                backdrop,
                '"/>',
                '<circle cx="256" cy="252" r="187" fill="#0b0b0d" opacity=".2"/>',
                '<path d="M108 178L72 62l122 73M404 178l36-116-122 73" fill="',
                fur,
                '" stroke="#241408" stroke-width="14" stroke-linejoin="round"/>',
                '<path d="M99 196c12-90 76-139 157-139s145 49 157 139v118c0 96-68 151-157 151S99 410 99 314z" fill="',
                fur,
                '" stroke="#241408" stroke-width="14"/>',
                '<path d="M104 203c49-14 80-47 98-101 18 45 47 68 87 72 48 5 83 24 119 57v88c0 89-63 139-152 139S104 408 104 319z" fill="#fff" opacity=".08"/>',
                '<path d="M132 149l-30-61 72 48zM380 149l30-61-72 48z" fill="#f0a07d" stroke="#241408" stroke-width="10"/>',
                '<path d="M146 230q47-37 91 2M275 232q44-39 91-2" fill="none" stroke="#241408" stroke-width="15" stroke-linecap="round"/>',
                '<ellipse cx="194" cy="253" rx="27" ry="33" fill="#f6e7c7"/><ellipse cx="318" cy="253" rx="27" ry="33" fill="#f6e7c7"/>',
                '<ellipse cx="194" cy="257" rx="13" ry="19" fill="',
                iris,
                '"/><ellipse cx="318" cy="257" rx="13" ry="19" fill="',
                iris,
                '"/>',
                '<circle cx="198" cy="250" r="5" fill="#fff"/><circle cx="322" cy="250" r="5" fill="#fff"/>',
                '<path d="M164 312c18-31 49-43 92-31 43-12 74 0 92 31v54c-20 47-64 66-92 66s-72-19-92-66z" fill="#f2d3a1" stroke="#241408" stroke-width="10"/>',
                '<path d="M230 320q26-18 52 0l-7 25q-19 17-38 0z" fill="#241408"/>',
                '<path d="M256 347v25m0 0q-25 26-51 4m51-4q25 26 51 4" fill="none" stroke="#241408" stroke-width="9" stroke-linecap="round"/>',
                '<g id="whiskers" fill="none" stroke="#241408" stroke-width="6" stroke-linecap="round"><path d="M206 342L82 320M205 360L70 365M306 342l124-22M307 360l135 5"/></g>',
                adornment,
                starMark,
                '<text x="32" y="474" fill="#f8edda" font-family="ui-monospace,monospace" font-size="20" font-weight="700">CRYPTO COUGARS / #',
                tokenId.toString(),
                "</text></svg>"
            );
    }

    function _accessorySVG(uint8 value) internal pure returns (string memory) {
        if (value == 1)
            return
                '<path d="M123 365q133 97 266 0" fill="none" stroke="#d53b42" stroke-width="22"/><circle cx="256" cy="426" r="19" fill="#ffd34d" stroke="#241408" stroke-width="8"/>';
        if (value == 2)
            return
                '<path d="M115 365q141 105 282 0l-39 91-102-27-102 27z" fill="#b32443" stroke="#241408" stroke-width="10"/>';
        if (value == 3)
            return
                '<path d="M174 104l30-70 52 52 52-52 30 70z" fill="#ffd34d" stroke="#241408" stroke-width="11"/>';
        if (value == 4)
            return
                '<g fill="#172130" fill-opacity=".72" stroke="#241408" stroke-width="11"><rect x="139" y="226" width="105" height="68" rx="28"/><rect x="268" y="226" width="105" height="68" rx="28"/><path d="M244 251h24"/></g>';
        if (value == 5)
            return
                '<path d="M132 379q124 88 248 0" fill="none" stroke="#f4c54d" stroke-width="16" stroke-dasharray="18 8"/>';
        return "";
    }

    function _coatName(uint8 value) internal pure returns (string memory) {
        string[6] memory names = [
            "Canyon Gold",
            "Tawny",
            "Sable",
            "Desert Rose",
            "Moonlit",
            "Obsidian"
        ];
        return names[value];
    }

    function _coatColor(uint8 value) internal pure returns (string memory) {
        string[6] memory colors = [
            "#c98236",
            "#dfa653",
            "#8c552c",
            "#bb715f",
            "#a99782",
            "#31343b"
        ];
        return colors[value];
    }

    function _eyeName(uint8 value) internal pure returns (string memory) {
        string[5] memory names = ["Amber", "Honey", "Jade", "Ice", "Ember"];
        return names[value];
    }

    function _eyeColor(uint8 value) internal pure returns (string memory) {
        string[5] memory colors = ["#d98119", "#f1b82d", "#4f9c68", "#78b9d2", "#b52d25"];
        return colors[value];
    }

    function _accessoryName(uint8 value) internal pure returns (string memory) {
        string[6] memory names = [
            "None",
            "Ranger Collar",
            "Canyon Bandana",
            "Sun Crown",
            "Night Glasses",
            "Gold Chain"
        ];
        return names[value];
    }

    function _backgroundName(uint8 value) internal pure returns (string memory) {
        string[6] memory names = [
            "Red Canyon",
            "Golden Hour",
            "Blue Mesa",
            "Night Ridge",
            "Sage Desert",
            "Rose Dusk"
        ];
        return names[value];
    }

    function _backgroundColor(uint8 value) internal pure returns (string memory) {
        string[6] memory colors = [
            "#7c2f2d",
            "#c66c2f",
            "#28506c",
            "#171d35",
            "#4e6650",
            "#744052"
        ];
        return colors[value];
    }

    function _ceilDiv(uint256 numerator, uint256 denominator) internal pure returns (uint256) {
        return numerator == 0 ? 0 : ((numerator - 1) / denominator) + 1;
    }

    function _setNextTokenIdForTest(uint256 nextTokenId_) internal {
        _nextTokenId = nextTokenId_;
    }
}

/// @dev Legacy name retained as a source-compatible alias for local tooling.
contract DecayedMint is CryptoCougars {}
