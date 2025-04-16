#include <iostream>
#include <vector>
#include <fstream>
#include <type_traits>
#include <string>
#include <variant>
#include <cstring>
#include <cstddef>

using Id = uint64_t;
using Buffer = std::vector<std::byte>;

enum class TypeId : Id {
    Uint,
    Float,
    String,
    Vector
};

namespace detail {
    
    class Any;

    template<typename T>
    constexpr TypeId type_to_id() {
        if constexpr (std::is_same_v<T, uint64_t>) return TypeId::Uint;
        else if constexpr (std::is_same_v<T, double>) return TypeId::Float;
        else if constexpr (std::is_same_v<T, std::string>) return TypeId::String;
        else return TypeId::Vector;
    }

    template<TypeId Id>
    struct id_to_type;

    template<> struct id_to_type<TypeId::Uint> { using type = uint64_t; };
    template<> struct id_to_type<TypeId::Float> { using type = double; };
    template<> struct id_to_type<TypeId::String> { using type = std::string; };
    template<> struct id_to_type<TypeId::Vector> { using type = std::vector<Any>; };

    template<typename T>
    void serialize_value(const T& value, Buffer& buffer) {
        const auto* ptr = reinterpret_cast<const std::byte*>(&value);
        buffer.insert(buffer.end(), ptr, ptr + sizeof(T));
    }

    template<>
    void serialize_value<std::string>(const std::string& value, Buffer& buffer) {
        uint64_t size = value.size();
        serialize_value(size, buffer);
        const auto* ptr = reinterpret_cast<const std::byte*>(value.data());
        buffer.insert(buffer.end(), ptr, ptr + value.size());
    }

    template<>
    void serialize_value<std::vector<Any>>(const std::vector<Any>& value, Buffer& buffer) {
        uint64_t size = value.size();
        serialize_value(size, buffer);
        for (const auto& item : value) {
            item.serialize(buffer);
        }
    }

    template<typename T>
    Buffer::const_iterator deserialize_value(Buffer::const_iterator begin, Buffer::const_iterator end, T& value) {
        if (std::distance(begin, end) < static_cast<std::ptrdiff_t>(sizeof(T))) {
            throw std::runtime_error("Invalid buffer size");
        }
        std::memcpy(&value, &*begin, sizeof(T));
        return begin + sizeof(T);
    }

    template<>
    Buffer::const_iterator deserialize_value<std::string>(Buffer::const_iterator begin, Buffer::const_iterator end, std::string& value) {
        uint64_t size = 0;
        begin = deserialize_value(begin, end, size);
        if (std::distance(begin, end) < static_cast<std::ptrdiff_t>(size)) {
            throw std::runtime_error("Invalid buffer size");
        }
        value.assign(reinterpret_cast<const char*>(&*begin), size);
        return begin + size;
    }

    template<>
    Buffer::const_iterator deserialize_value<std::vector<Any>>(Buffer::const_iterator begin, Buffer::const_iterator end, std::vector<Any>& value) {
        uint64_t size = 0;
        begin = deserialize_value(begin, end, size);
        value.resize(size);
        for (auto& item : value) {
            begin = item.deserialize(begin, end);
        }
        return begin;
    }
}

template<typename T>
class TypeWrapper {
public:
    using value_type = T;

    template<typename U, typename = std::enable_if_t<std::is_constructible_v<T, U>>>
    TypeWrapper(U&& value) : value_(std::forward<U>(value)) {}

    void serialize(Buffer& buffer) const {
        Id id = static_cast<Id>(detail::type_to_id<T>());
        detail::serialize_value(id, buffer);
        detail::serialize_value(value_, buffer);
    }

    Buffer::const_iterator deserialize(Buffer::const_iterator begin, Buffer::const_iterator end) {
        return detail::deserialize_value(begin, end, value_);
    }

    const T& get() const { return value_; }
    T& get() { return value_; }

    bool operator==(const TypeWrapper& other) const {
        return value_ == other.value_;
    }

private:
    T value_;
};

class IntegerType : public TypeWrapper<uint64_t> {
public:
    template<typename... Args>
    IntegerType(Args&&... args) : TypeWrapper<uint64_t>(std::forward<Args>(args)...) {}
};

class FloatType : public TypeWrapper<double> {
public:
    template<typename... Args>
    FloatType(Args&&... args) : TypeWrapper<double>(std::forward<Args>(args)...) {}
};

class StringType : public TypeWrapper<std::string> {
public:
    template<typename... Args>
    StringType(Args&&... args) : TypeWrapper<std::string>(std::forward<Args>(args)...) {}
};

class Any;

class VectorType : public TypeWrapper<std::vector<Any>> {
public:
    template<typename... Args>
    VectorType(Args&&... args) : TypeWrapper<std::vector<Any>>({ std::forward<Args>(args)... }) {}

    template<typename Arg>
    void push_back(Arg&& val) {
        this->get().emplace_back(std::forward<Arg>(val));
    }
};

class Any {
public:
    template<typename T>
    using IsValidType = std::disjunction<
        std::is_same<T, IntegerType>,
        std::is_same<T, FloatType>,
        std::is_same<T, StringType>,
        std::is_same<T, VectorType>,
        std::is_same<T, Any>>;

    template<typename T, typename = std::enable_if_t<IsValidType<std::decay_t<T>>::value>>
    Any(T&& value) {
        using DecayedT = std::decay_t<T>;
        if constexpr (std::is_same_v<DecayedT, IntegerType>) {
            data_ = value.get();
        }
        else if constexpr (std::is_same_v<DecayedT, FloatType>) {
            data_ = value.get();
        }
        else if constexpr (std::is_same_v<DecayedT, StringType>) {
            data_ = value.get();
        }
        else if constexpr (std::is_same_v<DecayedT, VectorType>) {
            data_ = value.get();
        }
        else if constexpr (std::is_same_v<DecayedT, Any>) {
            data_ = value.data_;
        }
    }

    void serialize(Buffer& buffer) const {
        std::visit([&buffer](const auto& value) {
            using T = std::decay_t<decltype(value)>;
            Id id = static_cast<Id>(detail::type_to_id<T>());
            detail::serialize_value(id, buffer);
            detail::serialize_value(value, buffer);
            }, data_);
    }

    Buffer::const_iterator deserialize(Buffer::const_iterator begin, Buffer::const_iterator end) {
        Id id = 0;
        begin = detail::deserialize_value(begin, end, id);

        switch (static_cast<TypeId>(id)) {
        case TypeId::Uint: {
            uint64_t value;
            begin = detail::deserialize_value(begin, end, value);
            data_ = value;
            break;
        }
        case TypeId::Float: {
            double value;
            begin = detail::deserialize_value(begin, end, value);
            data_ = value;
            break;
        }
        case TypeId::String: {
            std::string value;
            begin = detail::deserialize_value(begin, end, value);
            data_ = value;
            break;
        }
        case TypeId::Vector: {
            std::vector<Any> value;
            begin = detail::deserialize_value(begin, end, value);
            data_ = value;
            break;
        }
        default:
            throw std::runtime_error("Unknown type id");
        }

        return begin;
    }

    TypeId getPayloadTypeId() const {
        return static_cast<TypeId>(data_.index());
    }

    template<typename Type>
    auto& getValue() const {
        using T = typename Type::value_type;
        return std::get<T>(data_);
    }

    template<TypeId kId>
    auto& getValue() const {
        using T = typename detail::id_to_type<kId>::type;
        return std::get<T>(data_);
    }

    bool operator==(const Any& other) const {
        return data_ == other.data_;
    }

private:
    std::variant<uint64_t, double, std::string, std::vector<Any>> data_;
};

class Serializator {
public:
    template<typename T, typename = std::enable_if_t<Any::IsValidType<std::decay_t<T>>::value>>
    void push(T&& val) {
        storage_.emplace_back(std::forward<T>(val));
    }

    Buffer serialize() const {
        Buffer buffer;
        uint64_t size = storage_.size();
        detail::serialize_value(size, buffer);
        for (const auto& item : storage_) {
            item.serialize(buffer);
        }
        return buffer;
    }

    static std::vector<Any> deserialize(const Buffer& buffer) {
        std::vector<Any> result;
        auto it = buffer.begin();
        uint64_t size = 0;
        it = detail::deserialize_value(it, buffer.end(), size);
        result.reserve(size);
        for (uint64_t i = 0; i < size; ++i) {
            Any any;
            it = any.deserialize(it, buffer.end());
            result.push_back(any);
        }
        return result;
    }

    const std::vector<Any>& getStorage() const {
        return storage_;
    }

private:
    std::vector<Any> storage_;
};

int main() {
    std::ifstream raw;
    raw.open("raw.bin", std::ios_base::in | std::ios_base::binary);
    if (!raw.is_open())
        return 1;
    raw.seekg(0, std::ios_base::end);
    std::streamsize size = raw.tellg();
    raw.seekg(0, std::ios_base::beg);

    Buffer buff(size);
    raw.read(reinterpret_cast<char*>(buff.data()), size);

    auto res = Serializator::deserialize(buff);

    Serializator s;
    for (auto&& i : res)
        s.push(i);

    std::cout << (buff == s.serialize()) << '\n';

    return 0;
}
